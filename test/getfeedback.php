<?php
declare(strict_types=1);

header('Content-Type: application/json');

$feedbackFile = __DIR__ . '/data/feedback.jsonl';

if (!file_exists($feedbackFile)) {
    echo json_encode([]);
    exit;
}

$handle = fopen($feedbackFile, 'rb');
if (!$handle) {
    http_response_code(500);
    echo json_encode(['error' => 'Unable to read feedback']);
    exit;
}

$rows = [];
while (($line = fgets($handle)) !== false) {
    $line = trim($line);
    if ($line === '') {
        continue;
    }
    $decoded = json_decode($line, true);
    if (is_array($decoded)) {
        $rows[] = $decoded;
    }
}
fclose($handle);

echo json_encode($rows, JSON_UNESCAPED_UNICODE);
