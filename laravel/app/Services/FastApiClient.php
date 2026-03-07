<?php

declare(strict_types=1);

namespace App\Services;

use GuzzleHttp\Client;
use GuzzleHttp\Exception\GuzzleException;

class FastApiClient
{
    private Client $client;

    private string $baseUrl;

    private string $internalKey;

    public function __construct()
    {
        $this->baseUrl = config('services.fastapi.url');
        $this->internalKey = config('services.fastapi.key');
        $this->client = new Client(['timeout' => 120]);
    }

    /**
     * Non-streaming explain call — used by background jobs.
     *
     * @param  array<string, mixed>  $payload
     * @throws GuzzleException
     */
    public function explain(array $payload): string
    {
        $response = $this->client->post($this->baseUrl.'/explain', [
            'headers' => ['X-Internal-Key' => $this->internalKey],
            'json' => $payload,
        ]);

        return $response->getBody()->getContents();
    }

    /**
     * Streaming explain call — proxies SSE chunks to the output buffer.
     *
     * Calls $onChunk for each raw byte chunk as it arrives.
     *
     * @param  array<string, mixed>  $payload
     * @param  callable(string): void  $onChunk
     * @throws GuzzleException
     */
    public function streamExplain(array $payload, callable $onChunk): void
    {
        $response = $this->client->request('POST', $this->baseUrl.'/explain', [
            'headers' => [
                'X-Internal-Key' => $this->internalKey,
                'Accept' => 'text/event-stream',
            ],
            'json' => $payload,
            'stream' => true,
        ]);

        $body = $response->getBody();

        while (! $body->eof()) {
            $chunk = $body->read(1024);
            if ($chunk !== '') {
                $onChunk($chunk);
            }
        }
    }
}
