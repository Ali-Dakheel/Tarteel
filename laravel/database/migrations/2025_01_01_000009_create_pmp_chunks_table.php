<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up(): void
    {
        DB::statement('CREATE EXTENSION IF NOT EXISTS vector');

        Schema::create('pmp_chunks', function (Blueprint $table) {
            $table->id();
            $table->foreignId('lesson_id')->nullable()->constrained()->nullOnDelete();
            $table->text('content');
            $table->json('metadata')->nullable();
            $table->unsignedInteger('chunk_index')->default(0);
            $table->timestamps();
        });

        // Add pgvector column separately — Blueprint doesn't have a vector type
        DB::statement('ALTER TABLE pmp_chunks ADD COLUMN embedding vector(1024)');

        // Index for fast cosine similarity search
        DB::statement('CREATE INDEX pmp_chunks_embedding_idx ON pmp_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)');

        // Index for BM25 full-text search
        DB::statement("CREATE INDEX pmp_chunks_content_fts_idx ON pmp_chunks USING gin (to_tsvector('english', content))");
    }

    public function down(): void
    {
        Schema::dropIfExists('pmp_chunks');
    }
};
