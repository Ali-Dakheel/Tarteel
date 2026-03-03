<?php

declare(strict_types=1);

namespace Database\Factories;

use App\Models\Domain;
use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Str;

/**
 * @extends Factory<\App\Models\Lesson>
 */
class LessonFactory extends Factory
{
    public function definition(): array
    {
        $title = fake()->unique()->words(4, true);

        return [
            'domain_id' => Domain::factory(),
            'title' => ucwords($title),
            'slug' => Str::slug($title),
            'content' => fake()->paragraphs(3, true),
            'order' => fake()->unique()->numberBetween(1, 20),
            'is_free' => fake()->boolean(30),
        ];
    }
}
