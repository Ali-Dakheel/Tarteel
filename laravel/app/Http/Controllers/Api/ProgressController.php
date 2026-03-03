<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\UserProgressResource;
use App\Models\UserStreak;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class ProgressController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $progress = $request->user()
            ->progress()
            ->with('lesson:id,title,slug,domain_id')
            ->get();

        return response()->json([
            'completed_lessons' => $progress->whereNotNull('completed_at')->count(),
            'progress' => UserProgressResource::collection($progress),
        ]);
    }

    public function streak(Request $request): JsonResponse
    {
        $streak = UserStreak::query()->firstOrCreate(
            ['user_id' => $request->user()->id],
            ['current_streak' => 0, 'longest_streak' => 0]
        );

        return response()->json([
            'current_streak' => $streak->current_streak,
            'longest_streak' => $streak->longest_streak,
            'last_activity_date' => $streak->last_activity_date,
        ]);
    }
}
