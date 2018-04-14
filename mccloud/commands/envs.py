@packer.command()
def prod():
    """Works on prod environment"""
    global c
    c.env = 'prod'

@packer.command()
def stage():
    """Works on stage environment"""
    global c
    c.env = 'stage'

@packer.command()
def qa():
    """Works on qa environment"""
    global c
    c.env = 'qa'
