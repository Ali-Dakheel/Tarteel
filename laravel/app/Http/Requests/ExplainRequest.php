<?php

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
            'question_id' => ['required', 'integer', 'exists:questions,id'],
            'selected_option' => ['required', 'integer', 'min:0', 'max:3'],
            'lesson_id' => ['required', 'integer', 'exists:lessons,id'],
            'domain' => ['required', 'string'],
            'question_stem' => ['required', 'string'],
        ];
    }
}
