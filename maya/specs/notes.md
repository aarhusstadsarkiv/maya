# v2

## Get user clients

User doing this needs to be admin. Get list of clients.

/v2/clients/

```
{
  "data": [
    "created_at=datetime.datetime(2026, 2, 11, 8, 55, 16, 77934, tzinfo=datetime.timezone.utc) created_by=UUID('9e0a0602-xxx') id=UUID('d5152bab-xxxx') name='test client' type=<ClientType.BASE: 0>"
  ]
}
``` 

"id" is client id. 

## Get domains by client

/v2/clients/{id}/domains

"id" is domain id.

## Get Templates by client id and domain id

/v2/clients/{id}/domains/{domain_id}/templates

```
{
  "data": [
    {
      "created_at": "2026-04-29T10:31:12.612189+00:00",
      "created_by": "9e0a0602-xxxx",
      "domain_id": "1080b2c0-xxxx",
      "type": 0,
      "template": "Verification link:<br>\n<a href=\"{{ domain.url() }}/auth/verify/{{ token.token }}\">{{ domain.url() }}/auth/verify/{{ token.token }}</a>.",
      "subject": "register"
    },
    {
      "created_at": "2026-05-08T11:30:23.364396+00:00",
      "created_by": "9e0a0602-xxxx",
      "domain_id": "1080b2c0-xxxx",
      "type": 1,
      "template": "Password reset link:<br>\n<a href=\"{{ domain.url() }}/auth/reset-password/{{ token.token }}\">{{ domain.url() }}/auth/reset-password/{{ token.token }}</a>.",
      "subject": "New Password Reset"
    }
  ]
}
```

See: bin-local/generate_v2_email_template.py

In order to update mail templates. 
