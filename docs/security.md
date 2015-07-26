
Configurable security backends
=======================

We can not say in advance in what kind of environment this system will work.
Sometimes access to the system is physically limited, you trust all users and
don't want to bother them with passwords. In other cases, it is installed in 
university network with few thousands machines and you don't want somebody 
accidentally interrupt important experiment, so at least basic authorization
required. And sometimes it works in corporate environment with Single Sign On
(SSO), like Active Directory or Google Apps.

Because of this diversity there is no best single way to do user authorization. 
To address this diversity, system supports so called configurable security 
backends. In other words, it is possible to choose from several authorization
plugins or even write your own.

Security backend can be changed in system configuration file or admin console 
(web interface). In settings, it is configured as a path to Python class that 
implements authorization, with reasonable defaults provided.

Dummy backend
------------
This is not a real security backend - it is just a dummy that automatically
accepts all users as logged in with default username (Anonymous)

Password backend
------------

It is still not very secure, as passwords are transferred in plain text unless
system employs SSL certificates and forces SSL communication

###Configuration 

###Troubleshooting

Google/OpenID backend
------------



Admin authentication
===========

System has one special account to access settings, where auth backend can be
changed. This special account should not be affected by security backend and
always authorized using login/password pair. This login/password pair is
configured in main settings file.

API tokens
===========

Besides access to web interface, which is useless without API access, API
calls should also be authorized. At the same time, we don't want to use
user password in API calls because it is not secure and does not work with
third party backends, like OpenID. Instead, every user gets assigned API token,
which is generated in consistent manner for every user. Once user logs in, 
his api token is activated and can be used for API calls. After user logs out,
token will stay the same but it will not be accepted until user logs in again.

There are three possible places where API handlers will look for api token.

- Cookies. It is most useful if you use API from web interface (that is how
    default system interface works)
- HTTP basic auth headers, with user name api_token and token itself as a 
    password. Some clients do not have convenient way to pass cookies with 
    request, but for example support http://user:pasword@domain.tld format
- GET request parameter 'api_token'. This is the simplest but most insecure
    method. Yet all three methods do not protect against eavesdropping, this 
    one is especially insecure because GET parameters often logged by routers
    and proxies, so it can be accessed by a wider range of people.
