<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasOne;

class QuestionAttempt extends Model
{
    use HasFactory;

    protected $fillable = ['user_id', 'question_id', 'selected_option', 'is_correct', 'explained_at'];

    protected function casts(): array
    {
        return [
            'is_correct' => 'boolean',
            'explained_at' => 'datetime',
        ];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function question(): BelongsTo
    {
        return $this->belongsTo(Question::class);
    }

    public function xpEvent(): HasOne
    {
        return $this->hasOne(XpEvent::class);
    }
}
