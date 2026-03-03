<?php

declare(strict_types=1);

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\MarkProgressRequest;
use App\Http\Resources\LessonResource;
use App\Models\Lesson;
use App\Models\UserProgress;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class LessonController extends Controller
{
    public function show(Request $request, string $slug): JsonResponse
    {
        $lesson = Lesson::query()
            ->where('slug', $slug)
            ->with(['domain', 'questions'])
            ->firstOrFail();

        $userProgress = UserProgress::query()
            ->where('user_id', $request->user()->id)
            ->where('lesson_id', $lesson->id)
            ->first();

        $lesson->setRelation('userProgress', $userProgress);

        return $this->success(new LessonResource($lesson));
    }

    public function markProgress(MarkProgressRequest $request, string $slug): JsonResponse
    {
        $lesson = Lesson::query()->where('slug', $slug)->firstOrFail();

        $progress = UserProgress::query()->updateOrCreate(
            ['user_id' => $request->user()->id, 'lesson_id' => $lesson->id],
            [
                'completed_at' => now(),
                'time_spent_seconds' => $request->validated('time_spent_seconds'),
            ]
        );

        return $this->success(['completed_at' => $progress->completed_at]);
    }
}
