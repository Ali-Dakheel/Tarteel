<?php

declare(strict_types=1);

namespace App\Models;

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
}
