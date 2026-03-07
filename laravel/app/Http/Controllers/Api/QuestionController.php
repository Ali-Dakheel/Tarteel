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
use App\Services\GamificationService;
use Illuminate\Http\JsonResponse;

class QuestionController extends Controller
{
    public function __construct(private readonly GamificationService $gamification) {}

    public function attempt(QuestionAttemptRequest $request, Question $question): JsonResponse
    {
        $question->load('lesson.domain');

        $this->authorize('view', $question->lesson);

        /** @var User $user */
        $user = $request->user();
        $selectedOption = $request->selected_option;
        $isCorrect = $selectedOption === $question->correct_option;

        $isFirstAttempt = ! QuestionAttempt::query()
            ->where('user_id', $user->id)
            ->where('question_id', $question->id)
            ->exists();

        $attempt = QuestionAttempt::query()->create([
            'user_id' => $user->id,
            'question_id' => $question->id,
            'selected_option' => $selectedOption,
            'is_correct' => $isCorrect,
        ]);

        if ($isFirstAttempt) {
            $this->gamification->awardXp($user, $attempt, $isCorrect);

            if (! $isCorrect) {
                GenerateAiExplanationJob::dispatch($attempt, $question);
            }
        }

        $this->gamification->updateStreak($user);

        return $this->created(new QuestionAttemptResource($attempt->load('question')));
    }
}
