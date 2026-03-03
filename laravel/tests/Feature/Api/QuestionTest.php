<?php

declare(strict_types=1);

namespace Tests\Feature\Api;

use App\Jobs\GenerateAiExplanationJob;
use App\Models\Lesson;
use App\Models\Question;
use App\Models\User;
use App\Models\UserStreak;
use Illuminate\Support\Facades\Queue;
use Tests\TestCase;

class QuestionTest extends TestCase
{
    private User $user;

    private string $token;

    private Lesson $lesson;

    protected function setUp(): void
    {
        parent::setUp();
        Queue::fake();
        $this->user = User::factory()->create();
        $this->token = $this->user->createToken('api')->plainTextToken;
        $this->lesson = Lesson::factory()->create(['is_free' => true]);
    }

    public function test_correct_attempt_awards_10_xp(): void
    {
        $question = Question::factory()->create([
            'lesson_id' => $this->lesson->id,
            'correct_option' => 2,
        ]);

        $this->withToken($this->token)
            ->postJson("/api/v1/questions/{$question->id}/attempt", [
                'selected_option' => 2,
            ])
            ->assertStatus(201)
            ->assertJsonPath('data.is_correct', true);

        $this->assertDatabaseHas('xp_events', [
            'user_id' => $this->user->id,
            'amount' => 10,
            'reason' => 'correct_answer',
        ]);

        $this->assertEquals(10, $this->user->fresh()->xp);
    }

    public function test_incorrect_attempt_awards_2_xp(): void
    {
        $question = Question::factory()->create([
            'lesson_id' => $this->lesson->id,
            'correct_option' => 0,
        ]);

        $this->withToken($this->token)
            ->postJson("/api/v1/questions/{$question->id}/attempt", [
                'selected_option' => 1,
            ])
            ->assertStatus(201)
            ->assertJsonPath('data.is_correct', false);

        $this->assertDatabaseHas('xp_events', [
            'user_id' => $this->user->id,
            'amount' => 2,
            'reason' => 'attempted_answer',
        ]);

        $this->assertEquals(2, $this->user->fresh()->xp);
    }

    public function test_incorrect_attempt_dispatches_explanation_job(): void
    {
        $question = Question::factory()->create([
            'lesson_id' => $this->lesson->id,
            'correct_option' => 0,
        ]);

        $this->withToken($this->token)
            ->postJson("/api/v1/questions/{$question->id}/attempt", [
                'selected_option' => 1,
            ]);

        Queue::assertPushed(GenerateAiExplanationJob::class);
    }

    public function test_correct_attempt_does_not_dispatch_job(): void
    {
        $question = Question::factory()->create([
            'lesson_id' => $this->lesson->id,
            'correct_option' => 2,
        ]);

        $this->withToken($this->token)
            ->postJson("/api/v1/questions/{$question->id}/attempt", [
                'selected_option' => 2,
            ]);

        Queue::assertNotPushed(GenerateAiExplanationJob::class);
    }

    public function test_repeat_attempt_does_not_award_xp(): void
    {
        $question = Question::factory()->create([
            'lesson_id' => $this->lesson->id,
            'correct_option' => 0,
        ]);

        $this->withToken($this->token)
            ->postJson("/api/v1/questions/{$question->id}/attempt", ['selected_option' => 1]);

        $this->withToken($this->token)
            ->postJson("/api/v1/questions/{$question->id}/attempt", ['selected_option' => 1]);

        $this->assertDatabaseCount('xp_events', 1);
        $this->assertEquals(2, $this->user->fresh()->xp);
    }

    public function test_attempt_returns_403_for_paid_lesson_free_user(): void
    {
        $paidLesson = Lesson::factory()->create(['is_free' => false]);
        $question = Question::factory()->create([
            'lesson_id' => $paidLesson->id,
            'correct_option' => 0,
        ]);

        $this->withToken($this->token)
            ->postJson("/api/v1/questions/{$question->id}/attempt", ['selected_option' => 0])
            ->assertStatus(403);
    }

    public function test_attempt_creates_streak_on_first_activity(): void
    {
        $question = Question::factory()->create([
            'lesson_id' => $this->lesson->id,
            'correct_option' => 0,
        ]);

        $this->withToken($this->token)
            ->postJson("/api/v1/questions/{$question->id}/attempt", [
                'selected_option' => 0,
            ]);

        $this->assertDatabaseHas('user_streaks', [
            'user_id' => $this->user->id,
            'current_streak' => 1,
        ]);
    }

    public function test_attempt_increments_consecutive_streak(): void
    {
        UserStreak::factory()->create([
            'user_id' => $this->user->id,
            'current_streak' => 3,
            'last_activity_date' => now()->subDay()->toDateString(),
        ]);

        $question = Question::factory()->create([
            'lesson_id' => $this->lesson->id,
            'correct_option' => 0,
        ]);

        $this->withToken($this->token)
            ->postJson("/api/v1/questions/{$question->id}/attempt", [
                'selected_option' => 0,
            ]);

        $this->assertDatabaseHas('user_streaks', [
            'user_id' => $this->user->id,
            'current_streak' => 4,
        ]);
    }

    public function test_attempt_resets_streak_after_gap(): void
    {
        UserStreak::factory()->create([
            'user_id' => $this->user->id,
            'current_streak' => 10,
            'last_activity_date' => now()->subDays(3)->toDateString(),
        ]);

        $question = Question::factory()->create([
            'lesson_id' => $this->lesson->id,
            'correct_option' => 0,
        ]);

        $this->withToken($this->token)
            ->postJson("/api/v1/questions/{$question->id}/attempt", [
                'selected_option' => 0,
            ]);

        $this->assertDatabaseHas('user_streaks', [
            'user_id' => $this->user->id,
            'current_streak' => 1,
        ]);
    }

    public function test_attempt_does_not_double_count_same_day(): void
    {
        UserStreak::factory()->create([
            'user_id' => $this->user->id,
            'current_streak' => 5,
            'last_activity_date' => now()->toDateString(),
        ]);

        $question = Question::factory()->create([
            'lesson_id' => $this->lesson->id,
            'correct_option' => 0,
        ]);

        $this->withToken($this->token)
            ->postJson("/api/v1/questions/{$question->id}/attempt", [
                'selected_option' => 0,
            ]);

        $this->assertDatabaseHas('user_streaks', [
            'user_id' => $this->user->id,
            'current_streak' => 5,
        ]);
    }
}
