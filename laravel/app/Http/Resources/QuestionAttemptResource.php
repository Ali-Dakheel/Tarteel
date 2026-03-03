<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class QuestionAttemptResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'question_id' => $this->question_id,
            'selected_option' => $this->selected_option,
            'is_correct' => $this->is_correct,
            'correct_option' => $this->question->correct_option,
            'explanation' => $this->question->explanation,
            'explained_at' => $this->explained_at,
        ];
    }
}
