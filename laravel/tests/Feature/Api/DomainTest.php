<?php

declare(strict_types=1);

namespace Tests\Feature\Api;

use App\Models\Domain;
use App\Models\Lesson;
use App\Models\User;
use Tests\TestCase;

class DomainTest extends TestCase
{
    private function token(): string
    {
        return User::factory()->create()->createToken('api')->plainTextToken;
    }

    public function test_domains_index_returns_all_domains(): void
    {
        Domain::factory(3)->create();

        $this->withToken($this->token())
            ->getJson('/api/v1/domains')
            ->assertStatus(200)
            ->assertJsonCount(3, 'data')
            ->assertJsonStructure(['data' => [['id', 'name', 'slug', 'lesson_count']]]);
    }

    public function test_domains_index_requires_auth(): void
    {
        $this->getJson('/api/v1/domains')
            ->assertStatus(401);
    }

    public function test_domain_lessons_returns_lessons_for_slug(): void
    {
        $domain = Domain::factory()->create(['slug' => 'people']);
        Lesson::factory(2)->create(['domain_id' => $domain->id]);

        $this->withToken($this->token())
            ->getJson('/api/v1/domains/people/lessons')
            ->assertStatus(200)
            ->assertJsonCount(2, 'data')
            ->assertJsonStructure(['data' => [['id', 'title', 'question_count']]]);
    }

    public function test_domain_lessons_returns_404_for_unknown_slug(): void
    {
        $this->withToken($this->token())
            ->getJson('/api/v1/domains/nonexistent/lessons')
            ->assertStatus(404);
    }
}
