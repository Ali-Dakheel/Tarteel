<?php

declare(strict_types=1);

namespace Tests\Feature\Api;

use App\Models\Lesson;
use App\Models\Question;
use App\Models\User;
use App\Models\UserProgress;
use Tests\TestCase;

class LessonTest extends TestCase
{
    private User $user;

    private string $token;

    protected function setUp(): void
    {
        parent::setUp();
        $this->user = User::factory()->create();
        $this->token = $this->user->createToken('api')->plainTextToken;
    }

    public function test_lesson_show_returns_lesson_with_questions(): void
    {
        $lesson = Lesson::factory()->create(['slug' => 'test-lesson', 'is_free' => true]);
        Question::factory(3)->create(['lesson_id' => $lesson->id]);

        $this->withToken($this->token)
            ->getJson('/api/v1/lessons/test-lesson')
            ->assertStatus(200)
            ->assertJsonCount(3, 'data.questions')
            ->assertJsonStructure(['data' => ['id', 'title', 'domain', 'questions']]);
    }

    public function test_lesson_show_includes_user_progress_when_exists(): void
    {
        $lesson = Lesson::factory()->create(['slug' => 'progress-lesson', 'is_free' => true]);
        UserProgress::factory()->completed()->create([
            'user_id' => $this->user->id,
            'lesson_id' => $lesson->id,
        ]);

        $this->withToken($this->token)
            ->getJson('/api/v1/lessons/progress-lesson')
            ->assertStatus(200)
            ->assertJsonStructure(['data' => ['user_progress' => ['completed_at']]]);
    }

    public function test_lesson_show_returns_null_progress_when_none(): void
    {
        Lesson::factory()->create(['slug' => 'no-progress', 'is_free' => true]);

        $response = $this->withToken($this->token)
            ->getJson('/api/v1/lessons/no-progress')
            ->assertStatus(200);

        $this->assertNull($response->json('data.user_progress.completed_at'));
    }

    public function test_lesson_show_returns_404_for_unknown_slug(): void
    {
        $this->withToken($this->token)
            ->getJson('/api/v1/lessons/nonexistent')
            ->assertStatus(404);
    }

    public function test_lesson_show_returns_403_for_paid_lesson_free_user(): void
    {
        Lesson::factory()->create(['slug' => 'paid-lesson', 'is_free' => false]);

        $this->withToken($this->token)
            ->getJson('/api/v1/lessons/paid-lesson')
            ->assertStatus(403);
    }

    public function test_mark_progress_creates_progress_record(): void
    {
        $lesson = Lesson::factory()->create(['slug' => 'mark-lesson', 'is_free' => true]);

        $this->withToken($this->token)
            ->postJson('/api/v1/lessons/mark-lesson/progress', [
                'time_spent_seconds' => 300,
            ])
            ->assertStatus(200)
            ->assertJsonStructure(['data' => ['completed_at']]);

        $this->assertDatabaseHas('user_progress', [
            'user_id' => $this->user->id,
            'lesson_id' => $lesson->id,
            'time_spent_seconds' => 300,
        ]);
    }

    public function test_mark_progress_updates_existing_record(): void
    {
        Lesson::factory()->create(['slug' => 'update-lesson', 'is_free' => true]);

        $this->withToken($this->token)
            ->postJson('/api/v1/lessons/update-lesson/progress', ['time_spent_seconds' => 100]);

        $this->withToken($this->token)
            ->postJson('/api/v1/lessons/update-lesson/progress', ['time_spent_seconds' => 200]);

        $this->assertDatabaseCount('user_progress', 1);
        $this->assertDatabaseHas('user_progress', ['time_spent_seconds' => 200]);
    }

    public function test_mark_progress_fails_without_time_spent(): void
    {
        Lesson::factory()->create(['slug' => 'validate-lesson', 'is_free' => true]);

        $this->withToken($this->token)
            ->postJson('/api/v1/lessons/validate-lesson/progress', [])
            ->assertStatus(422)
            ->assertJsonValidationErrors(['time_spent_seconds']);
    }
}
