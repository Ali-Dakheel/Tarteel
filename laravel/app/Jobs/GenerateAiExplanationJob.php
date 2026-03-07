<?php

declare(strict_types=1);

namespace App\Jobs;

use App\Models\AiResponseCache;
use App\Models\Question;
use App\Models\QuestionAttempt;
use App\Services\FastApiClient;
use GuzzleHttp\Exception\GuzzleException;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Log;

class GenerateAiExplanationJob implements ShouldQueue
{
    use Queueable;

    public int $tries = 3;

    public int $backoff = 30;

    public function __construct(
        public readonly QuestionAttempt $attempt,
        public readonly Question $question,
    ) {
        $this->onQueue('ai-explanations');
    }

    public function handle(FastApiClient $fastApi): void
    {
        $lesson = $this->question->lesson;

        $payload = [
            'question_id' => $this->question->id,
            'selected_option' => $this->attempt->selected_option,
            'lesson_id' => $lesson->id,
            'domain' => $lesson->domain->slug ?? 'general',
            'question_stem' => $this->question->stem,
        ];

        try {
            $explanation = $fastApi->explain($payload);

            AiResponseCache::query()->updateOrCreate(
                ['query_hash' => AiResponseCache::makeKey($payload)],
                [
                    'response' => $explanation,
                    'retrieved_chunk_ids' => [],
                    'expires_at' => now()->addDays(7),
                ]
            );

            $this->attempt->update(['explained_at' => now()]);
        } catch (GuzzleException $e) {
            Log::error('GenerateAiExplanationJob failed', [
                'attempt_id' => $this->attempt->id,
                'error' => $e->getMessage(),
            ]);

            throw $e;
        }
    }
}
