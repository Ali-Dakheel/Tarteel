<?php

declare(strict_types=1);

namespace Database\Factories;

use App\Models\Question;
use App\Models\User;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<\App\Models\QuestionAttempt>
 */
class QuestionAttemptFactory extends Factory
{
    public function definition(): array
    {
        return [
            'user_id' => User::factory(),
            'question_id' => Question::factory(),
            'selected_option' => fake()->numberBetween(0, 3),
            'is_correct' => fake()->boolean(),
            'explained_at' => null,
        ];
    }

    public function correct(): static
    {
        return $this->state(fn (array $attributes) => [
            'is_correct' => true,
        ]);
    }

    public function incorrect(): static
    {
        return $this->state(fn (array $attributes) => [
            'is_correct' => false,
        ]);
    }
}
