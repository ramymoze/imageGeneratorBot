<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");
error_reporting(E_ALL);
ini_set('display_errors', 0);

function loadEnv($path = '.env') {
    if (file_exists($path)) {
        $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        foreach ($lines as $line) {
            if (strpos(trim($line), '#') === 0) continue;
            list($name, $value) = explode('=', $line, 2);
            $_ENV[trim($name)] = trim($value);
        }
    }
}
loadEnv();
$project_id = $_ENV['WEBSIM_PROJECT_ID'] ?? null;

if (!$project_id) {
    echo json_encode(["status" => "error", "message" => "Server configuration error: Project ID missing"]);
    exit;
}

function deco($text) {
    try {
        $decoded = urldecode($text);
        if (base64_encode(base64_decode($decoded, true)) === $decoded) {
            return base64_decode($decoded);
        }
        return $decoded;
    } catch (Exception $e) {
        return $text;
    }
}

function google_translate($text, $target_lang = "en") {
    $url = "https://translate.googleapis.com/translate_a/single";
    $params = http_build_query([
        "client" => "gtx",
        "sl" => "auto",
        "tl" => $target_lang,
        "dt" => "t",
        "q" => $text
    ]);

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url . "?" . $params);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $response = curl_exec($ch);
    
    if (curl_errno($ch)) {
        return false;
    }
    curl_close($ch);

    $result = json_decode($response, true);
    if (!is_array($result)) return $text;

    $translated_text = "";
    foreach ($result[0] as $item) {
        $translated_text .= $item[0];
    }

    return $translated_text;
}

if (!isset($_GET['text']) || trim($_GET['text']) === "") {
    echo json_encode(["status" => "error", "message" => "No text provided"]);
    exit;
}

$textInput = $_GET['text'];
$text = deco($textInput);
$translated = google_translate($text, "en");

if ($translated === false) {
    echo json_encode(["status" => "error", "message" => "Translation failed"]);
    exit;
}

$url = "https://api.websim.com/api/v1/inference/run_image_generation";

$payload = json_encode([
    "project_id" => $project_id,
    "prompt" => $translated,
    "aspect_ratio" => "1:1"
]);

$headers = [
    "User-Agent: Mozilla/5.0 (Linux; Android 12; SM-A025F Build/SP1A.210812.016) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.7151.61 Mobile Safari/537.36",
    "Content-Type: application/json",
    "origin: https://websim.com",
    "referer: https://websim.com/"
];

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

if (curl_errno($ch)) {
    echo json_encode(["status" => "error", "message" => "Curl error: " . curl_error($ch)]);
    curl_close($ch);
    exit;
}
curl_close($ch);

$data = json_decode($response, true);

if (isset($data['url'])) {
    $imageContent = file_get_contents($data['url']);
    if ($imageContent) {
        $base64 = base64_encode($imageContent);
        echo json_encode([
            "status" => "success", 
            "original_prompt" => $textInput,
            "translated_prompt" => $translated,
            "image_data" => "data:image/jpeg;base64," . $base64
        ]);
    } else {
        echo json_encode(["status" => "success", "image_url" => $data['url'], "note" => "Could not proxy image"]);
    }
} else {
    echo json_encode(["status" => "error", "message" => "API did not return an image URL", "debug" => $data]);
}
