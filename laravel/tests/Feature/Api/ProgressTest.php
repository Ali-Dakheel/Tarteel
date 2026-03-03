<?php

declare(strict_types=1);

namespace Tests\Feature\Api;

use App\Models\Lesson;
use App\Models\User;
use App\Models\UserProgress;
use App\Models\UserStreak;
use Tests\TestCase;

class ProgressTest extends TestCase
{
    private User $user;

    private string $token;

    protected function setUp(): void
    {
        parent::setUp();
        $this->user = User::factory()->create();
        $this->token = $this->user->createToken('api')->plainTextToken;
    }

    public function test_progress_index_returns_only_user_progress(): void
    {
        $lesson1 = Lesson::factory()->create();
        $lesson2 = Lesson::factory()->create();
        $otherUser = User::factory()->create();

        UserProgress::factory()->create(['user_id' => $this->user->id, 'lesson_id' => $lesson1->id]);
        UserProgress::factory()->create(['user_id' => $this->user->id, 'lesson_id' => $lesson2->id]);
        UserProgress::factory()->create(['user_id' => $otherUser->id, 'lesson_id' => $lesson1->id]);

        $this->withToken($this->token)
            ->getJson('/api/v1/progress')
            ->assertStatus(200)
            ->assertJsonCount(2, 'data.progress');
    }

    public function test_progress_includes_lesson_data(): void
    {
        $lesson = Lesson::factory()->create(['title' => 'Risk Management']);
        UserProgress::factory()->create([
            'user_id' => $this->user->id,
            'lesson_id' => $lesson->id,
        ]);

        $response = $this->withToken($this->token)
            ->getJson('/api/v1/progress')
            ->assertStatus(200);

        $this->assertEquals('Risk Management', $response->json('data.progress.0.lesson.title'));
    }

    public function test_progress_counts_completed_lessons(): void
    {
        $lesson1 = Lesson::factory()->create();
        $lesson2 = Lesson::factory()->create();

        UserProgress::factory()->completed()->create([
            'user_id' => $this->user->id,
            'lesson_id' => $lesson1->id,
        ]);
        UserProgress::factory()->create([
            'user_id' => $this->user->id,
            'lesson_id' => $lesson2->id,
            'completed_at' => null,
        ]);

        $this->withToken($this->token)
            ->getJson('/api/v1/progress')
            ->assertStatus(200)
            ->assertJsonPath('data.completed_lessons', 1);
    }

    public function test_streak_returns_current_streak(): void
    {
        UserStreak::factory()->create([
            'user_id' => $this->user->id,
            'current_streak' => 5,
            'longest_streak' => 10,
        ]);

        $this->withToken($this->token)
            ->getJson('/api/v1/streaks')
            ->assertStatus(200)
            ->assertJsonPath('data.current_streak', 5)
            ->assertJsonPath('data.longest_streak', 10);
    }

    public function test_streak_creates_default_if_not_exists(): void
    {
        $this->withToken($this->token)
            ->getJson('/api/v1/streaks')
            ->assertStatus(200)
            ->assertJsonPath('data.current_streak', 0);
    }
}
