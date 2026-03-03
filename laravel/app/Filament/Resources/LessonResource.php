<?php

declare(strict_types=1);

namespace App\Filament\Resources;

use App\Filament\Resources\LessonResource\Pages;
use App\Models\Domain;
use App\Models\Lesson;
use Filament\Actions\DeleteAction;
use Filament\Actions\EditAction;
use Filament\Forms\Components\RichEditor;
use Filament\Forms\Components\Select;
use Filament\Forms\Components\TextInput;
use Filament\Forms\Components\Toggle;
use Filament\Schemas\Components\Section;
use Filament\Schemas\Schema;
use Filament\Support\Icons\Heroicon;
use Filament\Tables\Columns\IconColumn;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Table;
use Illuminate\Support\Str;

class LessonResource extends \Filament\Resources\Resource
{
    protected static ?string $model = Lesson::class;

    protected static \BackedEnum|string|null $navigationIcon = Heroicon::OutlinedAcademicCap;

    protected static ?int $navigationSort = 2;

    public static function form(Schema $schema): Schema
    {
        return $schema->components([
            Section::make('Content')
                ->schema([
                    TextInput::make('title')
                        ->required()
                        ->maxLength(255)
                        ->live(onBlur: true)
                        ->afterStateUpdated(fn (string $state, callable $set) => $set('slug', Str::slug($state))),

                    TextInput::make('slug')
                        ->required()
                        ->maxLength(255)
                        ->unique(Lesson::class, 'slug', ignoreRecord: true),

                    Select::make('domain_id')
                        ->label('Domain')
                        ->options(Domain::query()->orderBy('order')->pluck('name', 'id'))
                        ->required()
                        ->searchable(),

                    RichEditor::make('content')
                        ->columnSpanFull(),
                ])
                ->columns(2),

            Section::make('Settings')
                ->schema([
                    TextInput::make('order')
                        ->numeric()
                        ->required()
                        ->default(1),

                    Toggle::make('is_free')
                        ->label('Free lesson')
                        ->default(false),
                ])
                ->columns(2),
        ]);
    }

    public static function table(Table $table): Table
    {
        return $table
            ->columns([
                TextColumn::make('title')
                    ->searchable()
                    ->sortable()
                    ->limit(50),

                TextColumn::make('domain.name')
                    ->sortable()
                    ->badge(),

                TextColumn::make('order')
                    ->sortable(),

                IconColumn::make('is_free')
                    ->boolean()
                    ->label('Free'),

                TextColumn::make('questions_count')
                    ->counts('questions')
                    ->label('Questions')
                    ->sortable(),
            ])
            ->defaultSort('domain_id')
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
            'index' => Pages\ListLessons::route('/'),
            'create' => Pages\CreateLesson::route('/create'),
            'edit' => Pages\EditLesson::route('/{record}/edit'),
        ];
    }
}
