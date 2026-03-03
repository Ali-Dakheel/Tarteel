<?php

declare(strict_types=1);

namespace Database\Factories;

use App\Models\Lesson;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<\App\Models\Question>
 */
class QuestionFactory extends Factory
{
    public function definition(): array
    {
        return [
            'lesson_id' => Lesson::factory(),
            'stem' => fake()->sentence().'?',
            'options' => [
                fake()->sentence(),
                fake()->sentence(),
                fake()->sentence(),
                fake()->sentence(),
            ],
            'correct_option' => fake()->numberBetween(0, 3),
            'explanation' => fake()->paragraph(),
            'difficulty' => fake()->randomElement(['easy', 'medium', 'hard']),
        ];
    }
}
