<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Lesson extends Model
{
    use HasFactory;

    protected $fillable = ['domain_id', 'title', 'slug', 'content', 'order', 'is_free'];

    protected function casts(): array
    {
        return [
            'is_free' => 'boolean',
        ];
    }

    public function domain(): BelongsTo
    {
        return $this->belongsTo(Domain::class);
    }

    public function questions(): HasMany
    {
        return $this->hasMany(Question::class);
    }

    public function chunks(): HasMany
    {
        return $this->hasMany(PmpChunk::class);
    }

    public function userProgress(): HasMany
    {
        return $this->hasMany(UserProgress::class);
    }
}
