<?php

declare(strict_types=1);

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\ExplainRequest;
use App\Models\AiResponseCache;
use App\Services\FastApiClient;
use GuzzleHttp\Exception\GuzzleException;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Log;
use Symfony\Component\HttpFoundation\StreamedResponse;

class TutorController extends Controller
{
    public function __construct(private readonly FastApiClient $fastApi) {}

    public function explain(ExplainRequest $request): StreamedResponse
    {
        $this->authorize('use-tutor');

        $payload = $request->validated();
        $cacheKey = AiResponseCache::makeKey($payload);

        $cached = AiResponseCache::active()
            ->where('query_hash', $cacheKey)
            ->first();

        if ($cached) {
            $cachedResponse = $cached->response;

            return response()->stream(function () use ($cachedResponse): void {
                echo $cachedResponse;
                if (ob_get_level() > 0) ob_flush();
                flush();
            }, Response::HTTP_OK, [
                'Content-Type' => 'text/event-stream',
                'Cache-Control' => 'no-cache',
                'X-Accel-Buffering' => 'no',
            ]);
        }

        return response()->stream(function () use ($payload): void {
            try {
                $this->fastApi->streamExplain($payload, function (string $chunk): void {
                    echo $chunk;
                    if (ob_get_level() > 0) ob_flush();
                    flush();
                });
            } catch (GuzzleException $e) {
                Log::error('TutorController SSE stream failed', [
                    'error' => $e->getMessage(),
                    'payload' => $payload,
                ]);
                echo "event: error\ndata: {\"error\": \"AI service unavailable\"}\n\n";
                if (ob_get_level() > 0) ob_flush();
                flush();
            }
        }, Response::HTTP_OK, [
            'Content-Type' => 'text/event-stream',
            'Cache-Control' => 'no-cache',
            'X-Accel-Buffering' => 'no',
        ]);
    }
}
