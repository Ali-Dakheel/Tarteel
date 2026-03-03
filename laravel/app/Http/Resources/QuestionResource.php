<?php

declare(strict_types=1);

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class QuestionResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'lesson_id' => $this->lesson_id,
            'stem' => $this->stem,
            'options' => $this->options,
            'difficulty' => $this->difficulty,
            // correct_option and explanation are intentionally omitted — exposed via QuestionAttemptResource after an attempt
        ];
    }
}
