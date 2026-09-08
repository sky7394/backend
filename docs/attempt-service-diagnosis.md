گزارش قرارداد و عیب‌یابی تلاش آزمون — 2026-09-07

این جدول قبل از هر تغییر سرویس یا تست، از AST نسخهٔ اولیه و اجرای مبنا استخراج شده است. اسامی متغیرها عین تست هستند؛ `_fake_uuid()` و `uuid4()` یک UUID تازه می‌سازند. فایل جامع ۲۳ تست و فایل دوم ۸ تست دارد.

| نام تست | تابع سرویس فراخوانی‌شده | امضای فراخوانی دقیق (args/kwargs) | نتیجه مورد انتظار (assertها) | status فعلی در مبنا |
|---|---|---|---|---|
| `test_normalize_answer_none_returns_empty` | normalize_answer | `normalize_answer(None)` | `assert normalize_answer(None) == ''` | passed |
| `test_normalize_answer_arabic_characters_to_persian` | normalize_answer | `normalize_answer('يكي'); normalize_answer('كبير')` | `assert normalize_answer('يكي') == 'یکی'; assert normalize_answer('كبير') == 'کبیر'` | passed |
| `test_normalize_answer_half_space_zwnj` | normalize_answer | `normalize_answer('می\u200cرود')` | `assert normalize_answer('می\u200cرود') == 'می رود'` | passed |
| `test_normalize_answer_persian_alef_preserved` | normalize_answer | `normalize_answer('آزمون')` | `assert normalize_answer('آزمون') == 'آزمون'` | passed |
| `test_normalize_answer_combined_and_extra_whitespace` | normalize_answer | `normalize_answer('  علي\u200cرضا  ')` | `assert normalize_answer('  علي\u200cرضا  ') == 'علی رضا'` | passed |
| `test_answers_are_equal_true_on_normalized_equality` | answers_are_equal | `answers_are_equal('علي', 'علی')` | `assert answers_are_equal('علي', 'علی') is True` | passed |
| `test_answers_are_equal_false_on_different_inputs` | answers_are_equal | `answers_are_equal('غلط', 'درست')` | `assert answers_are_equal('غلط', 'درست') is False` | passed |
| `test_answers_are_equal_empty_both_true` | answers_are_equal | `answers_are_equal('', '')` | `assert answers_are_equal('', '') is True` | passed |
| `test_answers_are_equal_one_empty_false` | answers_are_equal | `answers_are_equal('', 'پاسخ')` | `assert answers_are_equal('', 'پاسخ') is False` | passed |
| `test_start_attempt_exam_not_found_raises_valueerror` | start_attempt | `start_attempt(db_session, exam_id=9999, student_id=_fake_uuid())` | `pytest.raises(ValueError, match='Exam not found')` | failed |
| `test_start_attempt_success_returns_in_progress` | start_attempt | `start_attempt(db_session, exam_id=1, student_id=_fake_uuid())` | `assert result.id == attempt_id; assert result.status == IN_PROGRESS; assert result.start_time == started_at; db_session.add.assert_called_once_with(instance); db_session.commit.assert_awaited_once(); db_session.refresh.assert_awaited()` | failed |
| `test_get_attempt_not_found` | get_attempt | `get_attempt(db_session, attempt_id=_fake_uuid())` | `pytest.raises(ValueError)` | failed |
| `test_get_attempt_success` | get_attempt | `get_attempt(db_session, attempt_id=attempt.id)` | `assert result.id == attempt.id` | failed |
| `test_save_answer_attempt_not_found` | save_answer | `save_answer(db_session, attempt_id=_fake_uuid(), question_id=1, answer_text='پاسخ')` | `pytest.raises(ValueError)` | failed |
| `test_save_answer_success` | save_answer | `save_answer(db_session, attempt_id=attempt.id, question_id=5, answer_text='پاسخ ۵')` | `assert result.id == ans.id; db_session.add.assert_called_once_with(ans); db_session.commit.assert_awaited_once(); db_session.refresh.assert_awaited()` | failed |
| `test_submit_attempt_attempt_not_found` | submit_attempt | `submit_attempt(db_session, attempt_id=_fake_uuid(), student_id=_fake_uuid(), bulk=MagicMock(answers=[]))` | `pytest.raises(ValueError)` | failed |
| `test_submit_attempt_409_when_not_in_progress` | submit_attempt | `submit_attempt(db_session, attempt_id=finished.id, student_id=_fake_uuid(), bulk=request)` | `pytest.raises(ValueError)` | failed |
| `test_submit_attempt_success_bulk_grading` | submit_attempt | `submit_attempt(db_session, attempt_id=attempt.id, student_id=_fake_uuid(), bulk=request)` | `assert attempt.status == COMPLETED; db_session.commit.assert_awaited()` | failed |
| `test_get_attempt_result_not_found` | get_attempt_result | `get_attempt_result(db_session, attempt_id=_fake_uuid(), student_id=_fake_uuid())` | `pytest.raises(ValueError)` | failed |
| `test_get_attempt_result_success` | get_attempt_result | `get_attempt_result(db_session, attempt_id=attempt.id, student_id=_fake_uuid())` | `assert result is not None` | passed |
| `test_list_student_results_returns_items` | list_student_results | `list_student_results(db_session, student_id=_fake_uuid(), exam_id=1)` | `assert len(results) == 2` | passed |
| `test_list_student_results_empty` | list_student_results | `list_student_results(db_session, student_id=_fake_uuid())` | `assert results == []` | passed |
| `test_get_exam_results_is_alias_of_list_student_results` | فراخوانی سرویس ندارد (alias/router/schema) | `—` | `assert get_exam_results is list_student_results` | failed |
| `test_start_attempt_creates_in_progress_attempt` | attempt_service.start_attempt | `attempt_service.start_attempt(db, 10, student_id)` | `assert isinstance(result, ExamAttemptOut); assert result.id == created.id; assert result.status == attempt_service.IN_PROGRESS; db.commit.assert_awaited_once()` | failed |
| `test_save_answer_rejects_attempt_owned_by_another_student` | attempt_service.save_answer | `attempt_service.save_answer(db, uuid4(), uuid4(), 1, 'A')` | `pytest.raises(ValueError, match='Attempt not found')` | failed |
| `test_submit_attempt_bulk_grades_answers_and_calculates_percentage` | attempt_service.submit_attempt | `attempt_service.submit_attempt(db, attempt_id, student_id, ExamAttemptBulkSubmitRequest(answers=[{'question_id': 2, 'submitted_answer': 'wrong'}]))` | `assert isinstance(result, ExamResultOut); assert result.status == attempt_service.COMPLETED; assert result.total_score == 1.0; assert result.max_score == 2.0; assert result.percentage == 50.0; assert result.exam_title == 'Physics'; db.flush.assert_awaited_once(); db.commit.assert_awaited_once()` | failed |
| `test_submit_attempt_rejects_completed_attempt_without_mutation` | attempt_service.submit_attempt | `attempt_service.submit_attempt(db, attempt.id, student_id)` | `assert attempt.status == attempt_service.COMPLETED; assert attempt.total_score == 1.0; assert attempt.percentage == 50.0; db.commit.assert_not_awaited(); pytest.raises(ValueError, match='Attempt is already completed')` | failed |
| `test_submit_attempt_rolls_back_when_question_belongs_to_another_exam` | attempt_service.submit_attempt | `attempt_service.submit_attempt(db, attempt.id, student_id, payload)` | `db.rollback.assert_awaited_once(); db.commit.assert_not_awaited(); pytest.raises(ValueError, match='Question does not belong to this exam')` | failed |
| `test_exam_attempt_router_exposes_required_contract` | فراخوانی سرویس ندارد (alias/router/schema) | `—` | `assert ('POST', '/exam-attempts/exams/{exam_id}/start') in routes; assert ('PUT', '/exam-attempts/{attempt_id}/answers/{question_id}') in routes; assert ('POST', '/exam-attempts/{attempt_id}/submit') in routes; assert ('GET', '/exam-attempts/{attempt_id}') in routes; assert ('GET', '/exam-attempts/') in routes` | passed |
| `test_bulk_submission_schema_validates_answer_items` | فراخوانی سرویس ندارد (alias/router/schema) | `—` | `assert payload.answers[0].question_id == 1; assert AttemptAnswerUpsertRequest(submitted_answer='A').submitted_answer == 'A'` | passed |
| `test_submit_attempt_rejects_already_completed_attempt` | attempt_service.submit_attempt | `attempt_service.submit_attempt(db, attempt.id, student_id)` | `db.commit.assert_not_awaited(); pytest.raises(ValueError, match='Attempt is already completed')` | failed |

گام ۲: اجرای مبنا

محیط: Python 3.14.4، pytest 9.1.1. ابتدا import به دلیل نصب نبودن fpdf2 شکست خورد؛ وابستگی موجود در requirements.txt نصب شد، بدون تغییر فایل وابستگی‌ها.
فرمان --co فقط collection انجام داد: 31 tests collected. اجرای کامل: 17 failed, 14 passed, 4 warnings.
خروجی کامل collection، اولین شکست و همهٔ tracebackها در فایل‌های مجاور این گزارش نگهداری شده است.

سه الگوی غالب:

1. امضا: چهار TypeError در submit_attempt؛ تابع فقط دو پارامتر positional دارد ولی تست و endpoint سه یا چهار آرگومان می‌دهند. save_answer نیز student_id را به‌اشتباه question_id می‌گیرد؛ شکست مشاهده‌شدهٔ آن StopAsyncIteration است.
2. قرارداد persistence و داده: چهار AttributeError ناشی از coroutine، دو AttributeError برای نبودن ExamAttemptAnswer و bulk_grading، و یک ArgumentError ناشی از patch کردن کلاس ORM. در مبنا ValidationError رخ نداده چون خروجی اصلاً Pydantic نیست؛ بررسی مستقیم ExamAttemptOut.model_validate روی MagicMock دارای id/status، خطای student_id: uuid_type را نشان داد. برخی فیلدهای دیگر Mock حتی به مقادیر بی‌معنای عددی تبدیل می‌شوند؛ دادهٔ کامل مانع این موفقیت کاذب می‌شود.
3. رفتار و خروجی: سه DID NOT RAISE برای start/get/result و دو AssertionError برای هویت alias و نوع ExamAttemptOut. مجموع این دسته‌ها با StopAsyncIteration برابر ۱۷ است.

ImportError/NameError: پس از نصب وابستگی، هیچ‌کدام در ۳۱ تست رخ نداد. نبودن نمادهای patch شده AttributeError است، نه ImportError. ثابت‌های پنج‌گانه از ابتدا رشته‌های درست داشتند و علت شکست نبودند.

تحلیل کامل شکست اول: خط ۱۰۶ تست scalar را روی None تنظیم کرده است. خط ۹۴ سرویس execute را می‌خواند؛ AsyncMock تنظیم‌نشده نتیجهٔ AsyncMock می‌دهد. فراخوانی همگام scalar_one_or_none روی آن coroutine می‌سازد. _enrich_attempt_for_pydantic خطاهای دسترسی/نوشتن را می‌بلعد و coroutine truthy بازمی‌گردد. شرط mock_calls نیز مسیر خطای رکورد مفقود را حذف می‌کند. بنابراین در خط ۱۰۸ تست ValueError رخ نمی‌دهد و RuntimeWarning coroutine never awaited ظاهر می‌شود.

گام ۳: fixtureها و اثبات باگ تست

conftest.py فقط client/authenticated_client و anyio_backend دارد؛ هیچ session واقعی یا SQLite در دو فایل هدف ساخته نمی‌شود. db_session در خط ۴۴ فایل جامع MagicMock(spec=AsyncSession) است. make_db در خطوط ۲۶–۳۵ فایل دوم نیز همین نوع است، اما execute را با Result همگام و scalar_one_or_none تنظیم می‌کند. async بودن execute به معنی async بودن متدهای Result نیست.

شماره‌خط‌های زیر مربوط به نسخهٔ اولیهٔ tests/test_attempt_service_comprehensive.py هستند:

- ۱۰۶، ۱۱۸، ۱۴۶، ۱۶۰، ۱۷۴، ۱۸۶، ۲۰۵، ۲۲۲، ۲۳۷، ۲۶۰، ۲۷۳: scalar به‌جای execute تنظیم شده است. نسخهٔ ثبت‌شدهٔ سرویس در HEAD و تست دوم هر دو برای واکشی exam/attempt از execute استفاده می‌کنند. این fixture نتیجهٔ موردنظر را به عملیات اجراشده نمی‌دهد.
- ۱۲۳: patch کلاس ExamAttempt ساخت select(ExamAttempt) را نامعتبر می‌کند؛ traceback SQLAlchemy ArgumentError شاهد مستقیم است. به‌جای patch مدل، اثر add/refresh و نتیجهٔ query به‌صراحت تنظیم می‌شود.
- ۱۲۷ و ۱۳۳: start_time در هیچ‌یک از ExamAttempt (app/db/models.py:121) و ExamAttemptOut (app/schemas/exam_attempt.py:51) وجود ندارد؛ نام واقعی started_at است. فقط این assert از نظر نام فیلد تصحیح می‌شود.
- ۱۲۴–۱۲۷: exam_id، student_id، started_at، max_score و سایر فیلدهای خروجی روی MagicMock تنظیم نشده‌اند؛ UUID تولیدشده برای ورودی constructor به خودی‌خود attribute یک MagicMock نمی‌شود.
- ۱۵۴–۱۵۹: started_at و فیلدهای اختیاری به‌جای None، فرزند MagicMock هستند.
- ۱۸۳–۱۸۹: exam_id و answers تلاش و تمام فیلدهای پاسخ به‌جز id غایب‌اند؛ سؤال متعلق به آزمون نیز تنظیم نشده است. alias ExamAttemptAnswer در سرویس اضافه می‌شود و پاسخ واقعی از add گرفته می‌شود.
- ۲۳۳–۲۳۹: student_id، exam.title، answers و تاریخ‌ها غایب‌اند؛ text_answer/selected_option با BulkAttemptAnswerItem.submitted_answer ناسازگار است. ورودی با اسکیمای واقعی ساخته می‌شود؛ patch تابع نمره‌دهی و انتظار completed حفظ می‌شود.
- ۲۶۸–۲۷۳ و ۲۹۰–۲۹۱: رکوردهای نتیجه فاقد UUID دانش‌آموز، exam_id/title و تاریخ‌ها هستند. با دادهٔ کامل و مشخص جایگزین می‌شوند. assert is not None به‌تنهایی حتی برای coroutine موفق می‌شود و دلیل passed بودن قبلی تضمین صحت نیست.

تست دوم صریحاً ExamAttemptOut و ExamResultOut می‌خواهد؛ تست جامع هویت ORM را assert نمی‌کند. assertهای add به شیء ذخیره‌شده مربوط‌اند، نه نوع خروجی. بنابراین خروجی ثابت Pydantic با دادهٔ کامل قرارداد سازگار است. tests/test_exam_attempts.py و conftest.py تغییر نمی‌کنند.

گام ۴: تصمیم پیاده‌سازی پیش از تغییر کد

واکشی exam/attempt با execute و Result.scalar_one_or_none؛ اعتبار سؤال با scalar؛ خروجی ثابت Pydantic؛ student_id در SQL برای مسیرهای متعلق به دانش‌آموز؛ پذیرش امضای positional endpoint و kwargs جدول؛ bulk_grading یک تابع جدا با نتیجهٔ صریح answered/correct/total؛ alias واقعی برای get_exam_results؛ rollback همراه با بازپرتاب خطا؛ حذف تمام تشخیص‌های Mock و enrichment حدسی. db/session همان وابستگی تزریق‌شده است و نتایج آن در fixture صریحاً تنظیم می‌شوند. هیچ branch وابسته به نوع Mock لازم نیست.

گام ۵: تأیید

فرمان دقیق زیر با فعال بودن محیط مجازی پروژه اجرا شد:

```text
pytest tests/test_attempt_service_comprehensive.py tests/test_exam_attempts.py -v
============================== 31 passed in 1.55s ==============================
```

خروجی کامل: attempt-final.log. هیچ تستی skip/xfail نشده و هیچ هشدار coroutine باقی نمانده است. Ruff برای سرویس و فایل جامع موفق شد. مقایسهٔ AST تمام نام تست‌ها، assertها، pytest.raises و assertهای Mock را با نسخهٔ اولیه مقایسه کرد: تنها اختلاف assertion همان start_time → started_at است. تغییر fixtureها به‌صورت diff قابل بازبینی در attempt-fixture-fix.diff ثبت شده است. این نتیجه مربوط به دو فایل درخواستی است؛ کل مجموعهٔ پروژه اجرا نشده است.

امضاها و خروجی نهایی:

| تابع | پارامترها | خروجی |
|---|---|---|
| start_attempt | db, exam_id, student_id | ExamAttemptOut |
| get_attempt | db, attempt_id, student_id=None | ExamAttemptOut |
| save_answer | db, attempt_id, student_id=None, question_id=None, submitted_answer=None, *, answer_text=None | AttemptAnswerOut |
| submit_attempt | db, attempt_id, student_id, bulk=None | ExamResultOut |
| get_attempt_result | db, attempt_id, student_id=None | ExamResultOut |
| list_student_attempts | db, student_id, exam_id=None | list[ExamAttemptOut] |
| list_student_results / get_exam_results | db, student_id, exam_id=None | list[ExamResultOut] |

حذف student_id فقط برای فراخوانی داخلیِ مورد اعتماد پشتیبانی می‌شود؛ تمام endpointهای مربوط به دانش‌آموز آن را ارسال می‌کنند. در submit، خروجی پیش از commit اعتبارسنجی و از ORM جدا می‌شود؛ commit ناموفق هرگز خروجی موفق نمی‌دهد. بلوک‌های except باقی‌مانده فقط rollback و raise دارند و هیچ خطایی را سرکوب نمی‌کنند.

بررسی دیتابیس واقعی نیز موفق شد: اسکریپت attempt-sqlite-check.py با SQLite+aiosqlite در حافظه، بدون Mock، ساخت تلاش، upsert بدون پاسخ تکراری، کنترل مالکیت، rollback تغییر قبلی هنگام سؤال نامعتبر، ثبت نمرهٔ ۵۰٪، بازخوانی از session تازه و رد ارسال مجدد را بررسی کرد. هر دو حالت expire_on_commit=False و True موفق شدند. اجرای sandbox پس از import در هماهنگی thread/event loop متوقف شد؛ همان اسکریپت با مجوز خارج از sandbox با exit code 0 پایان یافت. هیچ دیتابیس پروژه‌ای استفاده نشد.

```text
PYTHONPATH=. .venv/bin/python docs/attempt-sqlite-check.py
SQLite lifecycle, ownership, upsert, rollback, persisted grading: PASS (expire_on_commit=False)
SQLite lifecycle, ownership, upsert, rollback, persisted grading: PASS (expire_on_commit=True)
```
