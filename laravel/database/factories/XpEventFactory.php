<?php

declare(strict_types=1);

namespace Database\Factories;

use App\Models\User;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<\App\Models\XpEvent>
 */
class XpEventFactory extends Factory
{
    public function definition(): array
    {
        return [
            'user_id' => User::factory(),
            'amount' => fake()->randomElement([2, 10]),
            'reason' => fake()->randomElement(['correct_answer', 'attempted_answer']),
            'question_attempt_id' => null,
        ];
    }
}
