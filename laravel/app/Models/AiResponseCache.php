<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;

class AiResponseCache extends Model
{
    protected $table = 'ai_response_cache';

    protected $fillable = ['query_hash', 'response', 'retrieved_chunk_ids', 'expires_at'];

    protected function casts(): array
    {
        return [
            'retrieved_chunk_ids' => 'array',
            'expires_at' => 'datetime',
        ];
    }

    /**
     * Generate a deterministic cache key from an explain payload.
     *
     * Matches the SHA256 key format used by the FastAPI cache layer.
     *
     * @param  array<string, mixed>  $payload
     */
    public static function makeKey(array $payload): string
    {
        $questionId = $payload['question_id'] ?? null;
        $selectedOption = $payload['selected_option'] ?? null;

        if ($questionId !== null) {
            return hash('sha256', $questionId.':'.$selectedOption);
        }

        return hash('sha256', 'freeform:'.strtolower(trim((string) ($payload['question_stem'] ?? ''))));
    }

    /** @param  Builder<AiResponseCache>  $query */
    public function scopeActive(Builder $query): void
    {
        $query->where('expires_at', '>', now());
    }
}
