<?php

declare(strict_types=1);

namespace App\Services;

use App\Models\QuestionAttempt;
use App\Models\User;
use App\Models\UserStreak;
use App\Models\XpEvent;

class GamificationService
{
    public const int XP_CORRECT = 10;

    public const int XP_ATTEMPTED = 2;

    /**
     * Award XP for a question attempt and record the XP event.
     */
    public function awardXp(User $user, QuestionAttempt $attempt, bool $isCorrect): void
    {
        $xpAmount = $isCorrect ? self::XP_CORRECT : self::XP_ATTEMPTED;
        $reason = $isCorrect ? 'correct_answer' : 'attempted_answer';

        XpEvent::query()->create([
            'user_id' => $user->id,
            'amount' => $xpAmount,
            'reason' => $reason,
            'question_attempt_id' => $attempt->id,
        ]);

        $user->increment('xp', $xpAmount);
    }

    /**
     * Update the user's daily streak. No-ops if already updated today.
     */
    public function updateStreak(User $user): void
    {
        $streak = UserStreak::query()->firstOrCreate(['user_id' => $user->id]);
        $today = now()->toDateString();

        if ($streak->last_activity_date?->toDateString() === $today) {
            return;
        }

        $yesterday = now()->subDay()->toDateString();
        $isConsecutive = $streak->last_activity_date?->toDateString() === $yesterday;

        $newStreak = $isConsecutive ? $streak->current_streak + 1 : 1;

        $streak->update([
            'current_streak' => $newStreak,
            'longest_streak' => max($streak->longest_streak, $newStreak),
            'last_activity_date' => $today,
        ]);
    }
}
