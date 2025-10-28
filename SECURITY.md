# Security Policy

## Environment Variables

This project requires several environment variables to be configured:

### Required Configuration

1. **Groq API Key**: Set `GROQ_API_KEY` in your `.env` file
   - Get your API key from [Groq Console](https://console.groq.com/keys)
   - Never commit your actual API key to version control

2. **Database Credentials**: The default credentials in `docker-compose.yml` are for development only
   - Change `POSTGRES_PASSWORD` and `REDIS_PASSWORD` for production
   - Use strong, unique passwords

### Security Best Practices

- Always use the provided `.env.example` as a template
- Never commit `.env` files containing real credentials
- Rotate API keys and passwords regularly
- Use Docker secrets for production deployments
- Enable firewall rules to restrict database access
- Monitor logs for suspicious activity

## Reporting Security Issues

If you discover a security vulnerability, please send an email to the repository maintainer rather than opening a public issue.

## Supported Versions

Only the latest version receives security updates.
