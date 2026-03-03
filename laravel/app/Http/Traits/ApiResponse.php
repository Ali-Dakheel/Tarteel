<?php

declare(strict_types=1);

namespace App\Http\Traits;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Resources\Json\JsonResource;
use Symfony\Component\HttpFoundation\Response;

trait ApiResponse
{
    protected function success(mixed $data = null, int $status = Response::HTTP_OK): JsonResponse
    {
        return response()->json(['data' => $data], $status);
    }

    protected function created(JsonResource|array $data): JsonResponse
    {
        return response()->json(['data' => $data], Response::HTTP_CREATED);
    }

    protected function noContent(): JsonResponse
    {
        return response()->json(null, Response::HTTP_NO_CONTENT);
    }

    protected function error(string $message, int $status = Response::HTTP_UNPROCESSABLE_ENTITY): JsonResponse
    {
        return response()->json(['message' => $message], $status);
    }
}
