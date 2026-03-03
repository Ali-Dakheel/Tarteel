<?php

declare(strict_types=1);

namespace Database\Factories;

use App\Models\User;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<\App\Models\UserStreak>
 */
class UserStreakFactory extends Factory
{
    public function definition(): array
    {
        return [
            'user_id' => User::factory(),
            'current_streak' => 0,
            'longest_streak' => 0,
            'last_activity_date' => null,
        ];
    }

    public function active(): static
    {
        return $this->state(fn (array $attributes) => [
            'current_streak' => fake()->numberBetween(1, 30),
            'longest_streak' => fake()->numberBetween(1, 60),
            'last_activity_date' => now()->toDateString(),
        ]);
    }
}
