def f():
  x = 0
  def g(y):
    global x
    x = y
    x += y
  g(2)
  print x

f()
