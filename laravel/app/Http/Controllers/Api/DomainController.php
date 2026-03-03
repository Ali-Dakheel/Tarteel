<?php

declare(strict_types=1);

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\DomainResource;
use App\Http\Resources\LessonResource;
use App\Models\Domain;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

class DomainController extends Controller
{
    public function index(): AnonymousResourceCollection
    {
        $domains = Domain::query()
            ->withCount('lessons')
            ->orderBy('order')
            ->get();

        return DomainResource::collection($domains);
    }

    public function lessons(string $slug): AnonymousResourceCollection
    {
        $domain = Domain::query()
            ->where('slug', $slug)
            ->firstOrFail();

        $lessons = $domain->lessons()
            ->withCount('questions')
            ->orderBy('order')
            ->get();

        return LessonResource::collection($lessons);
    }
}
