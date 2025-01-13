from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
import pandas as pd

@dataclass
class LessonProgress:
    completed: bool
    score: int
    completed_at: datetime
    attempts: int

@dataclass
class Achievement:
    name: str
    description: str
    icon: str
    unlocked: bool
    unlocked_at: datetime = None

class TradingLesson:
    def __init__(self, lesson_id: str, title: str, content: str, difficulty: str):
        self.lesson_id = lesson_id
        self.title = title
        self.content = content
        self.difficulty = difficulty
        self.quiz_questions = []
        
    def add_quiz_question(self, question: str, options: List[str], correct_answer: int):
        self.quiz_questions.append({
            'question': question,
            'options': options,
            'correct_answer': correct_answer
        })

class TradingEducation:
    def __init__(self):
        self.lessons = self._initialize_lessons()
        self.achievements = self._initialize_achievements()
        
    def _initialize_lessons(self) -> Dict[str, TradingLesson]:
        lessons = {}
        
        # MACD Strategy Lesson
        macd = TradingLesson(
            'macd_basics',
            'Understanding MACD Strategy',
            """
            The Moving Average Convergence Divergence (MACD) is a trend-following momentum indicator.
            Key concepts:
            1. MACD Line
            2. Signal Line
            3. MACD Histogram
            4. Trading Signals
            """,
            'Beginner'
        )
        macd.add_quiz_question(
            'What does MACD stand for?',
            [
                'Moving Average Convergence Divergence',
                'Multiple Average Calculation Display',
                'Market Analysis Chart Display',
                'Moving Analysis Chart Divergence'
            ],
            0
        )
        lessons['macd_basics'] = macd
        
        # Bollinger Bands Lesson
        bollinger = TradingLesson(
            'bollinger_basics',
            'Trading with Bollinger Bands',
            """
            Bollinger Bands are volatility bands placed above and below a moving average.
            Key concepts:
            1. Middle Band (20-day SMA)
            2. Upper Band (+2σ)
            3. Lower Band (-2σ)
            4. Volatility Measurement
            """,
            'Intermediate'
        )
        bollinger.add_quiz_question(
            'What do Bollinger Bands measure?',
            [
                'Market Volatility',
                'Only Price Direction',
                'Trading Volume',
                'Market Sentiment'
            ],
            0
        )
        lessons['bollinger_basics'] = bollinger
        
        return lessons
    
    def _initialize_achievements(self) -> Dict[str, Achievement]:
        return {
            'strategy_master': Achievement(
                name='Strategy Master',
                description='Complete all basic strategy lessons',
                icon='🎓',
                unlocked=False
            ),
            'quiz_ace': Achievement(
                name='Quiz Ace',
                description='Score 100% on any quiz',
                icon='🌟',
                unlocked=False
            ),
            'practice_pro': Achievement(
                name='Practice Pro',
                description='Complete 10 practice trades',
                icon='💪',
                unlocked=False
            )
        }
    
    def get_lesson(self, lesson_id: str) -> TradingLesson:
        return self.lessons.get(lesson_id)
    
    def get_all_lessons(self) -> List[TradingLesson]:
        return list(self.lessons.values())
    
    def check_quiz_answer(self, lesson_id: str, question_idx: int, answer: int) -> bool:
        lesson = self.lessons.get(lesson_id)
        if not lesson or question_idx >= len(lesson.quiz_questions):
            return False
        return lesson.quiz_questions[question_idx]['correct_answer'] == answer
    
    def get_achievements(self) -> List[Achievement]:
        return list(self.achievements.values())
    
    def unlock_achievement(self, achievement_id: str) -> bool:
        if achievement_id in self.achievements and not self.achievements[achievement_id].unlocked:
            self.achievements[achievement_id].unlocked = True
            self.achievements[achievement_id].unlocked_at = datetime.now()
            return True
        return False
