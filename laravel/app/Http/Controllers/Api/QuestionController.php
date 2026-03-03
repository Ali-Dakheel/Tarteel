<?php

declare(strict_types=1);

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\QuestionAttemptRequest;
use App\Http\Resources\QuestionAttemptResource;
use App\Jobs\GenerateAiExplanationJob;
use App\Models\Question;
use App\Models\QuestionAttempt;
use App\Models\User;
use App\Models\UserStreak;
use App\Models\XpEvent;
use Illuminate\Http\JsonResponse;

class QuestionController extends Controller
{
    public function attempt(QuestionAttemptRequest $request, Question $question): JsonResponse
    {
        /** @var User $user */
        $user = $request->user();
        $selectedOption = $request->selected_option;
        $isCorrect = $selectedOption === $question->correct_option;

        $attempt = QuestionAttempt::query()->create([
            'user_id' => $user->id,
            'question_id' => $question->id,
            'selected_option' => $selectedOption,
            'is_correct' => $isCorrect,
        ]);

        $this->awardXp($user, $attempt, $isCorrect);
        $this->updateStreak($user);

        if (! $isCorrect) {
            GenerateAiExplanationJob::dispatch($attempt, $question->load('lesson.domain'));
        }

        return $this->created(new QuestionAttemptResource($attempt->load('question')));
    }

    private function awardXp(User $user, QuestionAttempt $attempt, bool $isCorrect): void
    {
        $xpAmount = $isCorrect ? 10 : 2;
        $reason = $isCorrect ? 'correct_answer' : 'attempted_answer';

        XpEvent::query()->create([
            'user_id' => $user->id,
            'amount' => $xpAmount,
            'reason' => $reason,
            'question_attempt_id' => $attempt->id,
        ]);

        $user->increment('xp', $xpAmount);
    }

    private function updateStreak(User $user): void
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
