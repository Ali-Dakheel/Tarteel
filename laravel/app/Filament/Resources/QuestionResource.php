<?php

declare(strict_types=1);

namespace App\Filament\Resources;

use App\Filament\Resources\QuestionResource\Pages;
use App\Models\Lesson;
use App\Models\Question;
use Filament\Actions\DeleteAction;
use Filament\Actions\EditAction;
use Filament\Forms\Components\Select;
use Filament\Forms\Components\Textarea;
use Filament\Forms\Components\TextInput;
use Filament\Schemas\Components\Grid;
use Filament\Schemas\Components\Section;
use Filament\Schemas\Schema;
use Filament\Support\Icons\Heroicon;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Table;

class QuestionResource extends \Filament\Resources\Resource
{
    protected static ?string $model = Question::class;

    protected static \BackedEnum|string|null $navigationIcon = Heroicon::OutlinedQuestionMarkCircle;

    protected static ?int $navigationSort = 3;

    public static function form(Schema $schema): Schema
    {
        return $schema->components([
            Section::make('Question')
                ->schema([
                    Select::make('lesson_id')
                        ->label('Lesson')
                        ->options(
                            Lesson::query()
                                ->with('domain')
                                ->get()
                                ->mapWithKeys(fn (Lesson $lesson) => [
                                    $lesson->id => "[{$lesson->domain?->name}] {$lesson->title}",
                                ])
                        )
                        ->required()
                        ->searchable(),

                    Textarea::make('stem')
                        ->label('Question stem')
                        ->rows(3)
                        ->required()
                        ->columnSpanFull(),
                ])
                ->columns(2),

            Section::make('Options')
                ->schema([
                    Grid::make(2)
                        ->schema([
                            TextInput::make('options.0')->label('Option A')->required(),
                            TextInput::make('options.1')->label('Option B')->required(),
                            TextInput::make('options.2')->label('Option C')->required(),
                            TextInput::make('options.3')->label('Option D')->required(),
                        ]),

                    Select::make('correct_option')
                        ->options([
                            0 => 'A',
                            1 => 'B',
                            2 => 'C',
                            3 => 'D',
                        ])
                        ->required(),
                ]),

            Section::make('Details')
                ->schema([
                    Textarea::make('explanation')
                        ->rows(4)
                        ->columnSpanFull(),

                    Select::make('difficulty')
                        ->options([
                            'easy' => 'Easy',
                            'medium' => 'Medium',
                            'hard' => 'Hard',
                        ])
                        ->required(),
                ]),
        ]);
    }

    public static function table(Table $table): Table
    {
        return $table
            ->columns([
                TextColumn::make('stem')
                    ->searchable()
                    ->limit(60)
                    ->label('Question'),

                TextColumn::make('lesson.title')
                    ->sortable()
                    ->limit(30),

                TextColumn::make('difficulty')
                    ->badge()
                    ->color(fn (string $state): string => match ($state) {
                        'easy' => 'success',
                        'medium' => 'warning',
                        'hard' => 'danger',
                        default => 'gray',
                    }),

                TextColumn::make('correct_option')
                    ->formatStateUsing(fn (int $state): string => match ($state) {
                        0 => 'A', 1 => 'B', 2 => 'C', 3 => 'D',
                        default => (string) $state,
                    })
                    ->label('Answer'),
            ])
            ->recordActions([
                EditAction::make(),
                DeleteAction::make(),
            ])
            ->toolbarActions([
                \Filament\Actions\CreateAction::make(),
            ]);
    }

    public static function getPages(): array
    {
        return [
            'index' => Pages\ListQuestions::route('/'),
            'create' => Pages\CreateQuestion::route('/create'),
            'edit' => Pages\EditQuestion::route('/{record}/edit'),
        ];
    }
}
