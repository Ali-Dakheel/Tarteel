<?php

declare(strict_types=1);

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\ExplainRequest;
use App\Models\AiResponseCache;
use GuzzleHttp\Client;
use GuzzleHttp\Exception\GuzzleException;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\StreamedResponse;

class TutorController extends Controller
{
    public function explain(ExplainRequest $request): StreamedResponse
    {
        $this->authorize('use-tutor');

        $payload = $request->validated();
        $cacheKey = hash('sha256', $payload['question_id'].':'.$payload['selected_option']);

        $cached = AiResponseCache::query()
            ->where('query_hash', $cacheKey)
            ->where('expires_at', '>', now())
            ->first();

        if ($cached) {
            $cachedResponse = $cached->response;

            return response()->stream(function () use ($cachedResponse): void {
                echo $cachedResponse;
                ob_flush();
                flush();
            }, Response::HTTP_OK, [
                'Content-Type' => 'text/event-stream',
                'Cache-Control' => 'no-cache',
                'X-Accel-Buffering' => 'no',
            ]);
        }

        $fastapiUrl = config('services.fastapi.url');
        $internalKey = config('services.fastapi.key');

        return response()->stream(function () use ($payload, $fastapiUrl, $internalKey): void {
            $client = new Client(['timeout' => 120]);

            try {
                $response = $client->request('POST', $fastapiUrl.'/explain', [
                    'headers' => [
                        'X-Internal-Key' => $internalKey,
                        'Accept' => 'text/event-stream',
                    ],
                    'json' => $payload,
                    'stream' => true,
                ]);

                $body = $response->getBody();

                while (! $body->eof()) {
                    $chunk = $body->read(1024);
                    if ($chunk !== '') {
                        echo $chunk;
                        ob_flush();
                        flush();
                    }
                }
            } catch (GuzzleException $e) {
                echo "data: {\"error\": \"AI service unavailable\"}\n\n";
                ob_flush();
                flush();
            }
        }, Response::HTTP_OK, [
            'Content-Type' => 'text/event-stream',
            'Cache-Control' => 'no-cache',
            'X-Accel-Buffering' => 'no',
        ]);
    }
}
