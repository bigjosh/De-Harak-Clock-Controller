import web

# Do "sudo pip install web.py" to setup

urls = (
    '/', 'index'
    '/flash', 'flash'
)

class index:
    def GET(self):

	i = web.input(name=None)

	


        return "Hello, world!" + i.name

if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()
