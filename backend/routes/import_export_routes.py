import os
import zipfile
from datetime import datetime
from io import BytesIO

from flask import Blueprint, current_app, request, send_file
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import or_

import analytics
from accounts import create_account, unique_username
from audit import ACTION_EXPORT, ACTION_IMPORT, log_operation
from auth_utils import admin_required, get_current_user, login_required, role_required
from constants import (
    ATTACHMENT_CATEGORIES,
    COUNTED_STATUSES,
    STATUS_LABELS,
    STUDENT_CATEGORIES,
    TEACHER_CATEGORIES,
    categories_for,
    extra_labels,
    levels_for,
)
from extensions import db
from models import Achievement, Attachment, Student, Teacher, User
from services import build_achievement_query, normalize_dict_value
from security import normalize_text
from utils import error, parse_int, success
from validators import normalize_date, validate_student, validate_teacher

io_bp = Blueprint('io', __name__, url_prefix='/api')

HEADER_FILL = PatternFill('solid', fgColor='DCE6F1')
HEADER_FONT = Font(bold=True)


# --------------------------------------------------------------------------- #
# 通用
# --------------------------------------------------------------------------- #
def _cell(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    return normalize_text(value)


def _stamp():
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def _send_workbook(workbook, filename):
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


def _read_sheet(upload):
    if upload is None or not upload.filename:
        return None, '请选择要导入的 Excel 文件'
    if not upload.filename.lower().endswith(('.xlsx', '.xlsm')):
        return None, '仅支持 .xlsx 格式的 Excel 文件'
    try:
        workbook = load_workbook(upload, data_only=True)
    except Exception:
        return None, 'Excel 文件解析失败，请检查文件格式'
    sheet = workbook.active
    header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
    if header_row is None:
        return None, 'Excel 内容为空'
    raw_headers = [_cell(value) for value in header_row]
    headers = [name for name in raw_headers if name]
    if not headers:
        return None, 'Excel 第一行必须是表头'
    rows = []
    for values in sheet.iter_rows(min_row=2, values_only=True):
        if all(value is None or str(value).strip() == '' for value in values):
            continue
        # 按列位置对齐，避免中间出现空表头导致整体错位
        row = {}
        for header, value in zip(raw_headers, values):
            if header:
                row[header] = value
        rows.append(row)
    return (headers, rows), None


def _style_header(sheet, header_count):
    for index in range(1, header_count + 1):
        cell = sheet.cell(row=1, column=index)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center')
    sheet.freeze_panes = 'A2'


def _autosize(sheet, widths):
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width


# --------------------------------------------------------------------------- #
# 导入：教师
# --------------------------------------------------------------------------- #
@io_bp.post('/import/teachers')
@admin_required
def import_teachers():
    parsed, message = _read_sheet(request.files.get('file'))
    if parsed is None:
        return error(message)
    headers, rows = parsed
    if '姓名' not in headers:
        return error('Excel 缺少「姓名」列，请使用导入模板')

    options = request.form.to_dict()
    default_password = _cell(options.get('default_password')) or '123456'
    create_login = str(options.get('create_login', '1')) not in ('0', 'false', 'False')

    created = 0
    skipped = 0
    errors = []
    for index, row in enumerate(rows, start=2):
        name = _cell(row.get('姓名'))
        if not name:
            errors.append(f'第 {index} 行：姓名不能为空')
            skipped += 1
            continue

        payload, message = validate_teacher({
            'name': name,
            'department': row.get('所属院系'),
            'title': row.get('职称'),
            'email': row.get('邮箱'),
            'phone': row.get('联系电话'),
            'research_area': row.get('研究方向'),
        })
        if message:
            errors.append(f'第 {index} 行：{message}')
            skipped += 1
            continue

        username = _cell(row.get('登录名'))
        password = _cell(row.get('初始密码')) or default_password
        if username and User.query.filter_by(username=username).first():
            errors.append(f'第 {index} 行：登录名 {username} 已存在')
            skipped += 1
            continue
        if not create_login and not username:
            username = ''

        teacher = Teacher(
            name=payload['name'],
            department=normalize_dict_value('department', payload.get('department')),
            title=normalize_dict_value('title', payload.get('title')),
            email=payload.get('email', ''),
            phone=payload.get('phone', ''),
            research_area=payload.get('research_area', ''),
        )
        db.session.add(teacher)
        db.session.flush()
        if not username:
            username = unique_username('teacher')
        user = create_account(
            username, password, 'teacher',
            owner_type='teacher', owner_id=teacher.id,
            must_change_password=current_app.config.get('FORCE_PASSWORD_CHANGE', False),
        )
        teacher.user_id = user.id
        created += 1
    db.session.commit()
    log_operation(ACTION_IMPORT, 'teacher', None,
                  f'导入教师 {created} 条，跳过 {skipped} 条')
    return success(
        {'created': created, 'skipped': skipped, 'errors': errors},
        f'成功导入 {created} 条教师信息',
    )


# --------------------------------------------------------------------------- #
# 导入：学生
# --------------------------------------------------------------------------- #
@io_bp.post('/import/students')
@admin_required
def import_students():
    parsed, message = _read_sheet(request.files.get('file'))
    if parsed is None:
        return error(message)
    headers, rows = parsed
    required = ['学号', '姓名']
    missing = [name for name in required if name not in headers]
    if missing:
        return error('Excel 缺少列：' + '、'.join(missing) + '，请使用导入模板')

    options = request.form.to_dict()
    default_password = _cell(options.get('default_password')) or '123456'
    create_login = str(options.get('create_login', '1')) not in ('0', 'false', 'False')
    auto_advisor = str(options.get('auto_advisor', '1')) not in ('0', 'false', 'False')

    created = 0
    skipped = 0
    errors = []
    for index, row in enumerate(rows, start=2):
        payload, message = validate_student({
            'student_no': row.get('学号'),
            'name': row.get('姓名'),
            'grade': row.get('年级'),
            'major': row.get('专业'),
            'department': row.get('所属院系'),
            'class_name': row.get('班级'),
            'email': row.get('邮箱'),
            'phone': row.get('联系电话'),
        })
        if message:
            errors.append(f'第 {index} 行：{message}')
            skipped += 1
            continue
        if Student.query.filter_by(student_no=payload['student_no']).first():
            errors.append(f'第 {index} 行：学号 {payload["student_no"]} 已存在')
            skipped += 1
            continue

        username = _cell(row.get('登录名'))
        password = _cell(row.get('初始密码')) or default_password
        if username and User.query.filter_by(username=username).first():
            errors.append(f'第 {index} 行：登录名 {username} 已存在')
            skipped += 1
            continue

        student = Student(
            student_no=payload['student_no'],
            name=payload['name'],
            grade=normalize_dict_value('grade', payload.get('grade')),
            major=normalize_dict_value('major', payload.get('major')),
            department=normalize_dict_value('department', payload.get('department')),
            class_name=payload.get('class_name', ''),
            email=payload.get('email', ''),
            phone=payload.get('phone', ''),
        )
        db.session.add(student)
        db.session.flush()

        advisor_name = _cell(row.get('指导教师'))
        if advisor_name and auto_advisor:
            from routes.student_routes import set_advisors
            matched = Teacher.query.filter_by(name=advisor_name).first()
            if matched:
                set_advisors(student, [matched.id])
            else:
                errors.append(f'第 {index} 行：未找到指导教师「{advisor_name}」，已跳过绑定')

        if create_login or username:
            if not username:
                username = unique_username('student')
            user = create_account(
                username, password, 'student',
                owner_type='student', owner_id=student.id,
                must_change_password=current_app.config.get('FORCE_PASSWORD_CHANGE', False),
            )
            student.user_id = user.id
        created += 1
    db.session.commit()
    log_operation(ACTION_IMPORT, 'student', None,
                  f'导入学生 {created} 条，跳过 {skipped} 条')
    return success(
        {'created': created, 'skipped': skipped, 'errors': errors},
        f'成功导入 {created} 条学生信息',
    )


# --------------------------------------------------------------------------- #
# 导入：成果
# --------------------------------------------------------------------------- #
@io_bp.post('/import/achievements')
@admin_required
def import_achievements():
    parsed, message = _read_sheet(request.files.get('file'))
    if parsed is None:
        return error(message)
    headers, rows = parsed
    required = ['所属人类型', '所属人姓名', '成果类型', '成果名称']
    missing = [name for name in required if name not in headers]
    if missing:
        return error('Excel 缺少列：' + '、'.join(missing) + '，请使用导入模板')

    operator = get_current_user()
    options = request.form.to_dict()
    skip_duplicates = str(options.get('skip_duplicates', '1')) not in ('0', 'false', 'False')
    default_status = _cell(options.get('status')) or None

    created = 0
    skipped = 0
    duplicates = 0
    errors = []

    for index, row in enumerate(rows, start=2):
        type_raw = _cell(row.get('所属人类型')).lower()
        if type_raw in ('teacher', '教师', '老师'):
            owner_type = 'teacher'
        elif type_raw in ('student', '学生'):
            owner_type = 'student'
        else:
            errors.append(f'第 {index} 行：所属人类型应为「教师」或「学生」')
            skipped += 1
            continue

        owner_name = _cell(row.get('所属人姓名'))
        if not owner_name:
            errors.append(f'第 {index} 行：所属人姓名不能为空')
            skipped += 1
            continue
        if owner_type == 'teacher':
            owner = Teacher.query.filter_by(name=owner_name).first()
        else:
            owner = Student.query.filter(
                or_(Student.name == owner_name, Student.student_no == owner_name)
            ).first()
        if owner is None:
            errors.append(f'第 {index} 行：未找到'
                          f'{"教师" if owner_type == "teacher" else "学生"}「{owner_name}」')
            skipped += 1
            continue

        category = _cell(row.get('成果类型'))
        if category not in categories_for(owner_type):
            errors.append(f'第 {index} 行：成果类型「{category}」与该人员类型不匹配')
            skipped += 1
            continue

        title = _cell(row.get('成果名称'))
        if not title:
            errors.append(f'第 {index} 行：成果名称不能为空')
            skipped += 1
            continue

        year_raw = _cell(row.get('年份')) or str(datetime.now().year)
        try:
            year = int(float(year_raw))
        except (TypeError, ValueError):
            errors.append(f'第 {index} 行：年份「{year_raw}」不是有效数字')
            skipped += 1
            continue

        level = _cell(row.get('级别'))
        if level and level not in levels_for(category):
            errors.append(f'第 {index} 行：级别「{level}」不适用于「{category}」，'
                          f'可选：{"、".join(levels_for(category))}')
            skipped += 1
            continue

        if skip_duplicates:
            exists = Achievement.query.filter_by(
                owner_type=owner_type, owner_id=owner.id,
                category=category, title=title, year=year).first()
            if exists:
                duplicates += 1
                errors.append(f'第 {index} 行：成果「{title}」已存在（{year} 年），已跳过')
                skipped += 1
                continue

        # 类别专有字段：模板里以「中文标签」为表头
        labels = extra_labels(category)
        extra = {}
        extra_error = None
        for key, label in labels.items():
            if label not in headers:
                continue
            raw_value = row.get(label)
            if raw_value in (None, ''):
                continue
            text_value = _cell(raw_value)
            if key.endswith('_date'):
                parsed_date = normalize_date(text_value)
                if parsed_date is None:
                    extra_error = f'「{label}」日期格式应为 YYYY-MM-DD'
                    break
                extra[key] = parsed_date
            else:
                extra[key] = text_value
        if extra_error:
            errors.append(f'第 {index} 行：{extra_error}')
            skipped += 1
            continue

        advisor_id = None
        advisor_name = _cell(row.get('指导教师'))
        if advisor_name and owner_type == 'student':
            matched = Teacher.query.filter_by(name=advisor_name).first()
            if matched:
                advisor_id = matched.id
            else:
                errors.append(f'第 {index} 行：未找到指导教师「{advisor_name}」，已跳过绑定')

        status = _cell(row.get('审核状态')) or default_status or 'approved'
        status = {'已通过': 'approved', '待审核': 'pending', '草稿': 'draft',
                  '已驳回': 'rejected'}.get(status, status)
        if status not in STATUS_LABELS:
            status = 'approved'

        academic_year = _cell(row.get('学年')) or f'{year}-{year + 1}'
        achievement = Achievement(
            owner_type=owner_type,
            owner_id=owner.id,
            category=category,
            title=title,
            year=year,
            academic_year=academic_year,
            level=level,
            role_rank=_cell(row.get('完成人排序')),
            description=_cell(row.get('说明')),
            extra=extra,
            advisor_id=advisor_id,
            status=status,
            created_by=operator.id,
            updated_by=operator.id,
        )
        db.session.add(achievement)
        created += 1

    db.session.commit()
    log_operation(ACTION_IMPORT, 'achievement', None,
                  f'导入成果 {created} 条，跳过 {skipped} 条（其中重复 {duplicates} 条）')
    return success(
        {'created': created, 'skipped': skipped, 'duplicates': duplicates, 'errors': errors},
        f'成功导入 {created} 条成果数据',
    )


# --------------------------------------------------------------------------- #
# 导出：成果清单
# --------------------------------------------------------------------------- #
def _achievement_export_rows(items):
    rows = []
    for index, item in enumerate(items, start=1):
        data = item.to_dict()
        labels = extra_labels(item.category)
        row = {
            '序号': index,
            '所属人类型': '教师' if item.owner_type == 'teacher' else '学生',
            '所属人': data['owner_name'],
            '院系': data['owner_department'],
            '成果类型': item.category,
            '成果名称': item.title,
            '年份': item.year,
            '学年': data['academic_year'],
            '级别': item.level,
            '完成人排序': item.role_rank,
        }
        for key, label in labels.items():
            row[label] = item.extra_value(key)
        row.update({
            '指导教师': data.get('advisor_name', ''),
            '审核状态': STATUS_LABELS.get(item.status, item.status),
            '支撑材料数': data['attachment_count'],
            '支撑材料': '、'.join(a['original_name'] for a in data['attachments']),
            '认证指标点': '、'.join(f'{i["code"]} {i["name"]}' for i in data['indicators']),
            '说明': item.description,
            '录入时间': data['created_at'],
            '更新时间': data['updated_at'],
        })
        rows.append(row)
    return rows


EXPORT_BASE_HEADERS = ['序号', '所属人类型', '所属人', '院系', '成果类型', '成果名称',
                       '年份', '学年', '级别', '完成人排序']
EXPORT_TAIL_HEADERS = ['指导教师', '审核状态', '支撑材料数', '支撑材料', '认证指标点',
                       '说明', '录入时间', '更新时间']


@io_bp.get('/export/achievements')
@login_required
def export_achievements():
    user = get_current_user()
    items = build_achievement_query(user, request.args).all()
    rows = _achievement_export_rows(items)
    categories = sorted({item.category for item in items})
    extra_header = []
    seen = set()
    for category in categories:
        for label in extra_labels(category).values():
            if label not in seen:
                seen.add(label)
                extra_header.append(label)
    headers = EXPORT_BASE_HEADERS + extra_header + EXPORT_TAIL_HEADERS

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = '业绩成果'
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header, '') for header in headers])
    _style_header(sheet, len(headers))
    _autosize(sheet, [6, 10, 12, 16, 14, 40] + [16] * len(extra_header)
              + [12, 10, 10, 30, 20, 40, 20, 20])
    log_operation(ACTION_EXPORT, 'achievement', None,
                  f'导出成果清单 {len(rows)} 条（含筛选项）')
    return _send_workbook(workbook, f'业绩成果清单_{_stamp()}.xlsx')


@io_bp.get('/export/missing-evidence')
@login_required
def export_missing_evidence():
    user = get_current_user()
    args = dict(request.args)
    args.setdefault('has_attachment', '0')
    args.setdefault('status', 'approved')
    items = build_achievement_query(user, args).all()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = '缺件清单'
    headers = ['序号', '所属人类型', '所属人', '院系', '成果类型', '成果名称',
               '年份', '级别', '审核状态', '应补材料建议']
    sheet.append(headers)
    for index, item in enumerate(items, start=1):
        sheet.append([
            index,
            '教师' if item.owner_type == 'teacher' else '学生',
            item.to_dict()['owner_name'],
            item.to_dict()['owner_department'],
            item.category,
            item.title,
            item.year,
            item.level,
            STATUS_LABELS.get(item.status, item.status),
            '获奖证书/立项材料/成果正文等佐证扫描件',
        ])
    _style_header(sheet, len(headers))
    _autosize(sheet, [6, 10, 12, 16, 14, 44, 8, 10, 10, 34])
    log_operation(ACTION_EXPORT, 'achievement', None, f'导出缺件清单 {len(items)} 条')
    return _send_workbook(workbook, f'缺件清单_{_stamp()}.xlsx')


# --------------------------------------------------------------------------- #
# 导出：统计报表
# --------------------------------------------------------------------------- #
def _add_sheet(workbook, title, header, rows, widths=None):
    sheet = workbook.create_sheet(title)
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    _style_header(sheet, len(header))
    _autosize(sheet, widths or [26, 12] + [14] * max(len(header) - 2, 0))
    return sheet


@io_bp.get('/export/report')
@role_required('admin', 'reviewer')
def export_report():
    user = get_current_user()
    args = dict(request.args)
    args.setdefault('status', COUNTED_STATUSES[0])
    query = analytics.filtered_achievements(user, args)

    all_items = query.all()
    current_year = datetime.now().year
    counts = analytics.overview(user, query)

    workbook = Workbook()
    overview = workbook.active
    overview.title = '概览'
    overview.append(['统计指标', '数值'])
    overview.append(['教师总数', Teacher.query.count()])
    overview.append(['学生总数', Student.query.count()])
    overview.append(['成果总数', counts['achievements']])
    overview.append([f'{current_year} 年成果数', counts['this_year']])
    overview.append(['已归档支撑材料的成果数', counts['attachments']])
    overview.append(['缺少支撑材料的成果数', counts['missing_evidence']])
    overview.append(['待审核成果数', counts.get('pending', 0)])
    overview.append(['统计口径', f'审核状态={STATUS_LABELS.get(args["status"], args["status"])}'])
    overview.append(['生成时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    overview.append(['生成人', user.username])
    _style_header(overview, 2)
    _autosize(overview, [30, 28])

    # 成果明细
    rows = _achievement_export_rows(all_items)
    categories = sorted({item.category for item in all_items})
    extra_header, seen = [], set()
    for category in categories:
        for label in extra_labels(category).values():
            if label not in seen:
                seen.add(label)
                extra_header.append(label)
    detail_headers = EXPORT_BASE_HEADERS + extra_header + EXPORT_TAIL_HEADERS
    _add_sheet(workbook, '成果明细', detail_headers,
               [[row.get(header, '') for header in detail_headers] for row in rows],
               [6, 10, 12, 16, 14, 40] + [16] * len(extra_header)
               + [12, 10, 10, 30, 20, 40, 20, 20])

    _add_sheet(workbook, '成果类型分布', ['成果类型', '数量'],
               [[item['name'], item['value']] for item in
                analytics.grouped_counts(query, 'category')])
    _add_sheet(workbook, '年度成果趋势', ['年份', '数量', '同比(%)'],
               [[item['name'], item['value'], item['change_percent']]
                for item in analytics.yearly_trend(query)])
    _add_sheet(workbook, '成果级别分布', ['级别', '数量'],
               [[item['name'], item['value']] for item in
                analytics.grouped_counts(query, 'level')])
    _add_sheet(workbook, '院系成果分布', ['院系', '数量'],
               [[item['name'], item['value']] for item in
                analytics.grouped_counts(query, 'department')])

    person_rows = analytics.person_summary(query)
    _add_sheet(workbook, '师生汇总',
               ['人员类型', '姓名', '成果数', '已归档材料成果数', '缺件数', '最近年份'],
               [['教师' if row['owner_type'] == 'teacher' else '学生', row['name'],
                 row['achievement_count'], row['with_attachment'],
                 row['missing_evidence'], row['last_year']] for row in person_rows],
               [12, 14, 10, 20, 10, 12])

    missing = analytics.missing_evidence_rows(query)
    missing_rows = []
    for index, item in enumerate(missing, start=1):
        data = item.to_dict()
        missing_rows.append([index, '教师' if item.owner_type == 'teacher' else '学生',
                             data['owner_name'], data['owner_department'], item.category,
                             item.title, item.year, item.level, '需补充佐证材料'])
    _add_sheet(workbook, '缺件清单',
               ['序号', '人员类型', '姓名', '院系', '成果类型', '成果名称', '年份', '级别', '说明'],
               missing_rows, [6, 10, 12, 16, 14, 44, 8, 10, 26])

    coverage = analytics.indicator_coverage(query)
    _add_sheet(workbook, '指标点覆盖',
               ['指标点', '名称', '关联成果数', '占比(%)', '说明'],
               [[item['code'], item['name'], item['value'], item['percent'],
                 (item['description'] or '')[:120]] for item in coverage['items']],
               [10, 22, 12, 10, 60])

    _add_sheet(workbook, '指导教师成果',
               ['指导教师', '指导学生成果数'],
               [[item['name'], item['value']] for item in
                analytics.rankings(query, by='teacher', limit=200, only_advisors=True)],
               [20, 18])

    log_operation(ACTION_EXPORT, 'system', None,
                  f'导出统计报表（成果 {counts["achievements"]} 条，'
                  f'{len(workbook.sheetnames)} 个工作表）')
    return _send_workbook(workbook, f'专业业绩统计报表_{_stamp()}.xlsx')


# --------------------------------------------------------------------------- #
# 导出：佐证材料包（Excel 清单 + 分类附件）
# --------------------------------------------------------------------------- #
@io_bp.get('/export/package')
@login_required
def export_package():
    """一键打包某筛选范围的全部佐证材料：清单.xlsx + 按院系/人员分类的附件。"""
    user = get_current_user()
    args = dict(request.args)
    args.setdefault('status', COUNTED_STATUSES[0])
    query = analytics.filtered_achievements(user, args)
    items = query.all()
    upload_folder = current_app.config['UPLOAD_FOLDER']

    buffer = BytesIO()
    manifest_rows = []
    missing_rows = []
    packed = 0
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for index, item in enumerate(items, start=1):
            data = item.to_dict()
            department = data['owner_department'] or '未填写院系'
            person = f'{data["owner_name"]}_{item.owner_type}_{item.owner_id}'
            base_dir = os.path.join(department, person, f'{item.id}_{safe_title(item.title)}')
            attachments = item.attachment_rows()
            if not attachments:
                missing_rows.append([index, data['owner_name'], item.category, item.title,
                                     item.year, '无支撑材料'])
                continue
            for row in attachments:
                source = os.path.join(upload_folder, row.stored_path)
                if not os.path.exists(source):
                    missing_rows.append([index, data['owner_name'], item.category, item.title,
                                         item.year, f'文件缺失：{row.original_name}'])
                    continue
                target = os.path.join(base_dir, row.category or '其他', row.original_name)
                archive.write(source, target)
                packed += 1
                manifest_rows.append([
                    index, '教师' if item.owner_type == 'teacher' else '学生',
                    data['owner_name'], department, item.category, item.title,
                    item.year, item.level, STATUS_LABELS.get(item.status, item.status),
                    row.category, row.original_name, target,
                ])

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = '材料清单'
        headers = ['序号', '人员类型', '姓名', '院系', '成果类型', '成果名称', '年份',
                   '级别', '审核状态', '材料分类', '文件名', '包内路径']
        sheet.append(headers)
        for row in manifest_rows:
            sheet.append(row)
        _style_header(sheet, len(headers))
        _autosize(sheet, [6, 10, 12, 16, 14, 40, 8, 10, 10, 14, 30, 60])
        sheet.append([])
        sheet.append([f'共 {len(items)} 条成果，已打包 {packed} 份材料，'
                      f'{len(missing_rows)} 条存在缺件'])
        workbook_bytes = BytesIO()
        workbook.save(workbook_bytes)
        archive.writestr('材料清单.xlsx', workbook_bytes.getvalue())

        if missing_rows:
            missing_book = Workbook()
            missing_sheet = missing_book.active
            missing_sheet.title = '缺件清单'
            missing_sheet.append(['序号', '姓名', '成果类型', '成果名称', '年份', '问题'])
            for row in missing_rows:
                missing_sheet.append(row)
            _style_header(missing_sheet, 6)
            _autosize(missing_sheet, [6, 12, 14, 44, 8, 30])
            missing_bytes = BytesIO()
            missing_book.save(missing_bytes)
            archive.writestr('缺件清单.xlsx', missing_bytes.getvalue())

        archive.writestr('README.txt', (
            '专业师生业绩管理系统 - 佐证材料包\r\n'
            f'生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\r\n'
            f'生成人：{user.username}\r\n'
            f'成果数量：{len(items)}\r\n'
            f'材料数量：{packed}\r\n'
            f'筛选条件：{dict(args)}\r\n\r\n'
            '目录结构：<院系>/<所属人>/<成果序号_成果名称>/<材料分类>/<文件名>\r\n'
            '材料清单.xlsx 为全部材料的索引，缺件清单.xlsx 列出需要补充佐证的成果。\r\n'
        ).encode('utf-8-sig'))

    buffer.seek(0)
    log_operation(ACTION_EXPORT, 'attachment', None,
                  f'导出佐证材料包（成果 {len(items)} 条，材料 {packed} 份）')
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'佐证材料包_{_stamp()}.zip',
        mimetype='application/zip',
    )


def safe_title(title):
    name = str(title or '成果')
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, '_')
    return name[:60]


# --------------------------------------------------------------------------- #
# 导入模板
# --------------------------------------------------------------------------- #
@io_bp.get('/import/templates/teachers')
@admin_required
def teacher_template():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = '教师信息'
    headers = ['姓名', '所属院系', '职称', '邮箱', '联系电话', '研究方向', '登录名', '初始密码']
    sheet.append(headers)
    sheet.append(['张三', '计算机学院', '副教授', 'zhangsan@example.com', '13800000000',
                  '数据挖掘', 'teacher_demo', '123456'])
    _style_header(sheet, len(headers))
    _autosize(sheet, [12, 18, 12, 26, 16, 20, 18, 14])
    return _send_workbook(workbook, '教师信息导入模板.xlsx')


@io_bp.get('/import/templates/students')
@admin_required
def student_template():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = '学生信息'
    headers = ['学号', '姓名', '年级', '专业', '所属院系', '班级', '邮箱', '联系电话',
               '指导教师', '登录名', '初始密码']
    sheet.append(headers)
    sheet.append(['2021001', '李四', '2021级', '软件工程', '计算机学院', '软工2101',
                  'lisi@example.com', '13900000000', '张伟', 'student_demo', '123456'])
    _style_header(sheet, len(headers))
    _autosize(sheet, [12, 12, 10, 18, 18, 12, 26, 16, 12, 18, 14])
    return _send_workbook(workbook, '学生信息导入模板.xlsx')


@io_bp.get('/import/templates/achievements')
@admin_required
def achievement_template():
    """成果导入模板：首个工作表为通用表头，另附各类别专有字段与字典说明。"""
    workbook = Workbook()
    base = workbook.active
    base.title = '成果信息'
    headers = ['所属人类型', '所属人姓名', '成果类型', '成果名称', '年份', '学年',
               '级别', '完成人排序', '指导教师', '说明', '审核状态']
    base.append(headers)
    base.append(['教师', '张伟', '科研成果', '示例科研项目', datetime.now().year,
                 f'{datetime.now().year}-{datetime.now().year + 1}', '省部级',
                 '主持人', '', '示例说明，可删除', '已通过'])
    base.append(['学生', '刘洋', '学科竞赛', '示例学科竞赛奖项', datetime.now().year,
                 f'{datetime.now().year}-{datetime.now().year + 1}', '国家级',
                 '第一作者', '张伟', '示例说明，可删除', '已通过'])
    _style_header(base, len(headers))
    _autosize(base, [12, 14, 14, 34, 8, 12, 10, 12, 12, 34, 10])

    # 各类别的专有字段单独成表，便于按类别精确填写
    for category in TEACHER_CATEGORIES + STUDENT_CATEGORIES:
        sheet = workbook.create_sheet(category)
        extra = list(extra_labels(category).values())
        category_headers = ['所属人类型', '所属人姓名', '成果类型', '成果名称', '年份',
                            '学年', '级别'] + extra + ['指导教师', '说明', '审核状态']
        sheet.append(category_headers)
        sheet.append([
            '教师' if category in TEACHER_CATEGORIES else '学生',
            '张伟' if category in TEACHER_CATEGORIES else '刘洋',
            category, f'{category}示例名称', datetime.now().year,
            f'{datetime.now().year}-{datetime.now().year + 1}',
            levels_for(category)[0], *([''] * len(extra)),
            '', '示例数据，导入前请删除', '已通过',
        ])
        _style_header(sheet, len(category_headers))
        _autosize(sheet, [12, 14, 14, 34, 8, 12, 12] + [16] * len(extra) + [12, 30, 10])

    note = workbook.create_sheet('填写说明')
    note.append(['说明'])
    for line in (
        '1. 「成果信息」工作表为通用表头；如需填写类别专有字段（期刊、专利号等），'
        '请使用以类别命名的工作表。',
        '2. 「所属人类型」填「教师」或「学生」，「所属人姓名」可填姓名或学号。',
        '3. 「成果类型」必须与所属人类型匹配：教师 = ' + '、'.join(TEACHER_CATEGORIES)
        + '；学生 = ' + '、'.join(STUDENT_CATEGORIES) + '。',
        '4. 「级别」需从该成果类型的允许取值中选择，请参考「字段与字典」工作表。',
        '5. 重复「所属人 + 成果类型 + 成果名称 + 年份」的记录导入时会自动跳过并给出行号提示。',
        '6. 支撑材料请导入后在系统中逐条上传，可用「佐证材料包」导出核对缺件情况。',
    ):
        note.append([line])
    _autosize(note, [120])

    dictionary = workbook.create_sheet('字段与字典')
    dictionary.append(['成果类型', '允许级别', '专有字段'])
    for category in TEACHER_CATEGORIES + STUDENT_CATEGORIES:
        dictionary.append([category, '、'.join(levels_for(category)),
                           '、'.join(extra_labels(category).values())])
    _style_header(dictionary, 3)
    _autosize(dictionary, [18, 46, 60])
    return _send_workbook(workbook, '成果信息导入模板.xlsx')


@io_bp.get('/export/attachment-categories')
@login_required
def attachment_categories():
    return success(ATTACHMENT_CATEGORIES)