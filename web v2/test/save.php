<?php
declare(strict_types=1);

header('Content-Type: application/json');

$raw = file_get_contents('php://input');
$payload = json_decode($raw ?? '', true);

if (!is_array($payload)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Invalid JSON']);
    exit;
}

$dataDir = __DIR__ . '/data';
$resultsFile = $dataDir . '/results.jsonl';
$feedbackFile = $dataDir . '/feedback.jsonl';

if (!is_dir($dataDir) && !mkdir($dataDir, 0777, true) && !is_dir($dataDir)) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Unable to create data directory']);
    exit;
}

$entryType = $payload['type'] ?? 'trial';

if ($entryType === 'feedback') {
    $record = [
        'type' => 'feedback',
        'pid' => $payload['pid'] ?? null,
        'nickname' => $payload['nickname'] ?? null,
        'conditions' => $payload['conditions'] ?? [],
        'device_type' => $payload['device_type'] ?? null,
        'comment' => $payload['comment'] ?? '',
        'ts' => $payload['ts'] ?? gmdate('c')
    ];
    $line = json_encode($record, JSON_UNESCAPED_UNICODE);
    if ($line === false) {
        http_response_code(500);
        echo json_encode(['ok' => false, 'error' => 'Encoding error']);
        exit;
    }
    $result = file_put_contents($feedbackFile, $line . PHP_EOL, FILE_APPEND | LOCK_EX);
    if ($result === false) {
        http_response_code(500);
        echo json_encode(['ok' => false, 'error' => 'Unable to write feedback']);
        exit;
    }
    echo json_encode(['ok' => true]);
    exit;
}

$payload['ts'] = $payload['ts'] ?? gmdate('c');

$line = json_encode($payload, JSON_UNESCAPED_UNICODE);
if ($line === false) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Encoding error']);
    exit;
}

$result = file_put_contents($resultsFile, $line . PHP_EOL, FILE_APPEND | LOCK_EX);
if ($result === false) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Unable to write file']);
    exit;
}

echo json_encode(['ok' => true]);
