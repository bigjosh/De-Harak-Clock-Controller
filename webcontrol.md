To enable the web-based clock controls...

1. Install apache...

```
sudo apt-get install apache2 -y
```

2. Enable cgi...

```
a2enmod cgi
```

3. Restart server

```
sudo service apache2 restart
```

Now put any cgi files in `/usr/lib/cgi-bin` and `chmod +x` them. 

Here is a simple `test.cgi`...

```
#!/bin/bash

echo -e "Content-type: text/html\n\n"

echo "<h1>Hello World</h1>"
```

