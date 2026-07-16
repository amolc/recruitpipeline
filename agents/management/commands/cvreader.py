from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from api.models import Application
from agents.models import CVExtract
from agents.extractor import process_cv


class Command(BaseCommand):
    help = 'Extract data from a candidate CV/resume and save structured results'

    def add_arguments(self, parser):
        parser.add_argument('application_id', type=int, help='Application ID to process')
        parser.add_argument('--reprocess', action='store_true', help='Replace existing extract if one exists')

    def handle(self, *args, **options):
        app_id = options['application_id']
        try:
            application = Application.objects.get(id=app_id)
        except Application.DoesNotExist:
            raise CommandError(f'Application with id {app_id} not found')

        if not application.resume:
            raise CommandError(f'Application {app_id} has no resume file')

        if not options['reprocess']:
            existing = CVExtract.objects.filter(application=application).first()
            if existing:
                self.stdout.write(f'CVExtract already exists for {application.full_name} (id={existing.id}). Use --reprocess to overwrite.')
                return

        file_path = Path(settings.MEDIA_ROOT) / application.resume.name
        if not file_path.exists():
            raise CommandError(f'Resume file not found: {file_path}')

        self.stdout.write(f'Extracting text from {file_path}...')
        data = process_cv(file_path)

        extract, created = CVExtract.objects.update_or_create(
            application=application,
            defaults={
                'raw_text': data['raw_text'],
                'summary': data['summary'],
                'skills': data['skills'],
                'experience': data['experience'],
                'education': data['education'],
                'certifications': data['certifications'],
                'languages': data.get('languages', []),
                'contact': data.get('contact', {}),
                'total_experience_years': data.get('total_experience_years'),
                'status': 'completed',
            }
        )

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} CVExtract (id={extract.id}) for {application.full_name}\n'
            f'  Summary:    {data["summary"][:80]}...\n'
            f'  Skills:     {len(data["skills"])} found\n'
            f'  Experience: {len(data["experience"])} entries\n'
            f'  Education:  {len(data["education"])} entries\n'
            f'  Certs:      {len(data["certifications"])} found'
        ))
