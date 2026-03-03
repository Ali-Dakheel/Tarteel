<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class LessonResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'domain_id' => $this->domain_id,
            'title' => $this->title,
            'slug' => $this->slug,
            'content' => $this->when($this->relationLoaded('domain'), fn () => $this->content),
            'order' => $this->order,
            'is_free' => $this->is_free,
            'question_count' => $this->whenCounted('questions'),
            'domain' => new DomainResource($this->whenLoaded('domain')),
            'questions' => QuestionResource::collection($this->whenLoaded('questions')),
            'user_progress' => new UserProgressResource($this->whenLoaded('userProgress')),
        ];
    }
}
