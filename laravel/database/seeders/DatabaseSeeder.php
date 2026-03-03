<?php

declare(strict_types=1);

namespace Database\Seeders;

use App\Models\Domain;
use App\Models\Lesson;
use App\Models\Question;
use App\Models\User;
use App\Models\UserStreak;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use Illuminate\Support\Str;

class DatabaseSeeder extends Seeder
{
    use WithoutModelEvents;

    public function run(): void
    {
        $testUser = User::factory()->create([
            'name' => 'Test User',
            'email' => 'test@example.com',
        ]);

        UserStreak::factory()->create(['user_id' => $testUser->id]);

        $pmpDomains = [
            [
                'name' => 'People',
                'slug' => 'people',
                'description' => 'Leadership and team management skills for project managers.',
                'order' => 1,
            ],
            [
                'name' => 'Process',
                'slug' => 'process',
                'description' => 'Technical aspects of managing projects effectively.',
                'order' => 2,
            ],
            [
                'name' => 'Business Environment',
                'slug' => 'business-environment',
                'description' => 'Connection between projects and organizational strategy.',
                'order' => 3,
            ],
        ];

        foreach ($pmpDomains as $index => $domainData) {
            $domain = Domain::create($domainData);

            $lessonTitles = $this->lessonTitlesFor($domainData['slug']);

            foreach ($lessonTitles as $lessonIndex => $lessonTitle) {
                $lesson = Lesson::create([
                    'domain_id' => $domain->id,
                    'title' => $lessonTitle,
                    'slug' => Str::slug($lessonTitle),
                    'content' => "# {$lessonTitle}\n\nThis lesson covers key concepts related to {$lessonTitle} in the context of PMP certification.\n\n## Key Topics\n\n- Topic 1\n- Topic 2\n- Topic 3",
                    'order' => $lessonIndex + 1,
                    'is_free' => $lessonIndex === 0,
                ]);

                Question::factory(5)->create(['lesson_id' => $lesson->id]);
            }
        }
    }

    /** @return array<int, string> */
    private function lessonTitlesFor(string $domainSlug): array
    {
        return match ($domainSlug) {
            'people' => [
                'Leadership Styles and Situational Leadership',
                'Team Building and Development',
                'Conflict Resolution and Negotiation',
                'Stakeholder Engagement',
                'Coaching and Mentoring',
            ],
            'process' => [
                'Project Initiation and Charter',
                'Scope Management and WBS',
                'Schedule Management and Critical Path',
                'Risk Management',
                'Quality and Change Management',
            ],
            'business-environment' => [
                'Organizational Strategy and Alignment',
                'Benefits Realization Management',
                'Governance and Compliance',
                'Project Selection Methods',
                'Agile and Hybrid Methodologies',
            ],
            default => [],
        };
    }
}
