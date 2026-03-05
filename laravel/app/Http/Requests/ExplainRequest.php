<?php

declare(strict_types=1);

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class ExplainRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'question_id' => ['nullable', 'integer', 'exists:questions,id'],
            'selected_option' => ['nullable', 'integer', 'min:0', 'max:3'],
            'lesson_id' => ['nullable', 'integer', 'exists:lessons,id'],
            'domain' => ['required', 'string'],
            'question_stem' => ['required', 'string'],
        ];
    }
}
