<?php

declare(strict_types=1);

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class UserProgressResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'lesson_id' => $this->lesson_id,
            'completed_at' => $this->completed_at,
            'time_spent_seconds' => $this->time_spent_seconds,
            'lesson' => new LessonResource($this->whenLoaded('lesson')),
        ];
    }
}
