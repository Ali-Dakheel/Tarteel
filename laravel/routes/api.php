<?php

use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\DomainController;
use App\Http\Controllers\Api\LessonController;
use App\Http\Controllers\Api\ProgressController;
use App\Http\Controllers\Api\QuestionController;
use App\Http\Controllers\Api\TutorController;
use Illuminate\Support\Facades\Route;

// Public auth routes
Route::prefix('auth')->group(function () {
    Route::post('register', [AuthController::class, 'register']);
    Route::post('login', [AuthController::class, 'login']);
});

// Authenticated routes
Route::middleware('auth:sanctum')->group(function () {
    // Auth
    Route::prefix('auth')->group(function () {
        Route::post('logout', [AuthController::class, 'logout']);
        Route::get('me', [AuthController::class, 'me']);
    });

    // Content
    Route::get('domains', [DomainController::class, 'index']);
    Route::get('domains/{slug}/lessons', [DomainController::class, 'lessons']);
    Route::get('lessons/{slug}', [LessonController::class, 'show']);
    Route::post('lessons/{slug}/progress', [LessonController::class, 'markProgress']);

    // Questions
    Route::post('questions/{question}/attempt', [QuestionController::class, 'attempt']);

    // AI Tutor (SSE proxy)
    Route::post('tutor/explain', [TutorController::class, 'explain']);

    // User data
    Route::get('progress', [ProgressController::class, 'index']);
    Route::get('streaks', [ProgressController::class, 'streak']);
});
