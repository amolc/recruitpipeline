from django.core.management.base import BaseCommand
from api.models import Skill

COMMON_SKILLS = {
    'Programming Languages': [
        'Python', 'JavaScript', 'TypeScript', 'Java', 'C#', 'C++', 'C', 'Go', 'Rust', 'Ruby',
        'PHP', 'Swift', 'Kotlin', 'Scala', 'R', 'Perl', 'Dart', 'Lua', 'Haskell', 'Elixir',
    ],
    'Web Frameworks': [
        'Django', 'Flask', 'FastAPI', 'React', 'Next.js', 'Vue.js', 'Nuxt.js', 'Angular',
        'Svelte', 'Express.js', 'NestJS', 'Spring Boot', 'ASP.NET', 'Ruby on Rails', 'Laravel',
        'Symfony', 'Phoenix', 'Play Framework',
    ],
    'Databases': [
        'PostgreSQL', 'MySQL', 'SQLite', 'MongoDB', 'Redis', 'Elasticsearch', 'Oracle',
        'SQL Server', 'MariaDB', 'Cassandra', 'DynamoDB', 'Firebase', 'Supabase', 'Neo4j',
    ],
    'DevOps & Cloud': [
        'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'Terraform', 'Ansible', 'Jenkins',
        'GitHub Actions', 'GitLab CI', 'CircleCI', 'Prometheus', 'Grafana', 'Nginx',
        'Linux', 'Bash', 'Helm', 'ArgoCD',
    ],
    'AI & Data Science': [
        'Machine Learning', 'Deep Learning', 'Natural Language Processing', 'Computer Vision',
        'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'LangChain', 'OpenAI API',
        'Hugging Face', 'LLM Fine-tuning', 'RAG', 'Vector Databases', 'Data Analysis',
        'Tableau', 'Power BI', 'Apache Spark', 'Hadoop',
    ],
    'Mobile Development': [
        'React Native', 'Flutter', 'iOS Development', 'Android Development', 'SwiftUI',
        'Jetpack Compose', 'Xamarin', 'Ionic',
    ],
    'Soft Skills': [
        'Project Management', 'Agile', 'Scrum', 'Team Leadership', 'Communication',
        'Problem Solving', 'Critical Thinking', 'Technical Writing', 'Code Review',
        'Mentoring', 'Public Speaking', 'Cross-functional Collaboration',
    ],
    'Tools & Platforms': [
        'Git', 'GitHub', 'GitLab', 'Bitbucket', 'Jira', 'Confluence', 'Slack', 'Figma',
        'Postman', 'Swagger', 'Sentry', 'Datadog', 'New Relic', 'Splunk',
    ],
    'Testing': [
        'Unit Testing', 'Integration Testing', 'End-to-End Testing', 'pytest', 'Jest',
        'Selenium', 'Cypress', 'Playwright', 'Load Testing', 'TDD',
    ],
    'Frontend': [
        'HTML', 'CSS', 'Tailwind CSS', 'Bootstrap', 'Sass', 'Redux', 'GraphQL',
        'Webpack', 'Vite', 'REST API Design', 'Responsive Design', 'Accessibility',
    ],
}


class Command(BaseCommand):
    help = 'Seed common skills into the database'

    def handle(self, *args, **options):
        created_count = 0
        for category, skills in COMMON_SKILLS.items():
            for name in skills:
                _, created = Skill.objects.get_or_create(name=name, defaults={'category': category})
                if created:
                    created_count += 1
                    self.stdout.write(f'  + {name} ({category})')
        self.stdout.write(self.style.SUCCESS(f'Done. Created {created_count} new skills.'))
