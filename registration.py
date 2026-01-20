import shutil
from pathlib import Path
from models_db import init_registration_db, create_student, add_document, list_student_documents

UPLOAD_DIR = Path("uploads")

BACHELOR_PROGRAMMES = [
    "Double Degree in Computer Science: Artificial Intelligence",
    "Computer Science",
    "Robotics",
    "Computer Engineering and Electronics",
    "Aviation Engineering",
    "Transport and Logistics",
    "Business and Management",
]

MASTER_PROGRAMMES = [
    "New! Double Degree in Management of Information Systems: IT Project Management",
    "Double Degree in Computer Science: Data Analytics and Artificial Intelligence",
    "Double degree in Aviation Management",
    "Computer Science: Software Engineering",
    "Management of Information Systems",
    "Computer Engineering and Electronics",
    "Business and Management",
    "Intelligent Transport and Smart Logistics",
]

DOC_TYPES = [
    "Passport/ID",
    "Diploma/Certificate",
    "Transcript",
    "English Proficiency",
    "Motivation Letter",
    "CV/Resume",
]

def init():
    init_registration_db()
    UPLOAD_DIR.mkdir(exist_ok=True)

def register_student(full_name: str, email: str, program_level: str, program_name: str, notes: str = "") -> int:
    program_level = program_level.strip()
    program_name = program_name.strip()

    if program_level not in {"Bachelor", "Master"}:
        raise ValueError("Program level must be Bachelor or Master.")

    valid = BACHELOR_PROGRAMMES if program_level == "Bachelor" else MASTER_PROGRAMMES
    if program_name not in valid:
        raise ValueError("Invalid programme selected for the chosen level.")

    return create_student(
        full_name=full_name.strip(),
        email=email.strip(),
        program_level=program_level,
        program_name=program_name,
        notes=(notes or "").strip(),
    )

def save_uploaded_file(student_id: int, doc_type: str, file_path: str) -> str:
    if doc_type not in DOC_TYPES:
        raise ValueError("Invalid document type.")

    src = Path(file_path)
    if not src.exists():
        raise FileNotFoundError("Uploaded file not found.")

    student_folder = UPLOAD_DIR / f"student_{student_id}"
    student_folder.mkdir(parents=True, exist_ok=True)

    dest = student_folder / src.name
    if dest.exists():
        dest = student_folder / f"{dest.stem}_copy{dest.suffix}"

    shutil.copy(src, dest)
    add_document(student_id=student_id, doc_type=doc_type, original_filename=src.name, saved_path=str(dest))
    return str(dest)

def get_documents(student_id: int):
    return list_student_documents(student_id)
