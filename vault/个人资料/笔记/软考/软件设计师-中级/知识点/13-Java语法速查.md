---
tags:
  - 软考
  - Java
  - 语法速查
---

# Java 语法速查表（Python 对照版）

> 专为软考下午第 5/6 题设计模式代码填空准备。左边是 Java（考试用），右边是 Python（你熟悉的）。

## 1. 类与对象

| 概念 | Java | Python |
|------|------|--------|
| 定义类 | `class Dog { }` | `class Dog:` |
| 构造方法 | `public Dog(String name) { this.name = name; }` | `def __init__(self, name): self.name = name` |
| 创建对象 | `Dog d = new Dog("旺财");` | `d = Dog("旺财")` |
| 当前对象引用 | `this.name` | `self.name` |
| 调用自己的构造器 | `this("默认值");` | `super().__init__()` (不完全是) |

## 2. 访问修饰符

| 修饰符 | Java 含义 | Python 等价（约定） |
|--------|----------|-------------------|
| `public` | 任何地方都能访问 | 直接写方法名（公开） |
| `private` | 只有本类能访问 | `__method`（双下划线前缀） |
| `protected` | 本类 + 子类 + 同包 | `_method`（单下划线前缀） |
| _(默认)_ | 同包内可访问 | （无等价） |

## 3. 继承与接口

| 概念 | Java | Python |
|------|------|--------|
| 继承类 | `class Dog extends Animal` | `class Dog(Animal)` |
| 实现接口 | `class Dog implements Runnable` | `class Dog(Runnable)` (鸭子类型，无接口) |
| 同时继承+实现 | `class A extends B implements C, D` | `class A(B, C, D)` (多继承) |
| 调用父类方法 | `super.doIt();` | `super().do_it()` |
| 抽象类 | `abstract class Animal` | `class Animal(ABC)` |
| 抽象方法 | `abstract void eat();` | `@abstractmethod` + `def eat(self): ...` |
| 接口 | `interface Runner { void run(); }` | Python 无接口（用 ABC 或鸭子类型） |

## 4. 关键字速查

| 关键字 | 含义 | 出现在什么题型 |
|--------|------|---------------|
| `this` | 引用当前对象 | 构造方法填空 |
| `super` | 引用父类对象 | 子类调用父类构造器 |
| `static` | 静态成员（属于类而非对象） | 工厂方法、单例模式 |
| `final` | 不可变（类不能被继承，方法不能被重写，变量是常量） | 单例模式、不可变对象 |
| `abstract` | 抽象（类不可实例化，方法无实现体） | **高频填空** |
| `extends` | 继承父类 | **高频填空** |
| `implements` | 实现接口 | **高频填空** |
| `new` | 创建对象实例 | **高频填空** |
| `void` | 方法无返回值 | 方法签名填空 |
| `null` | 空引用 | 初始化、比较 |

## 5. 方法签名格式

```
[修饰符] [static] [abstract] 返回值类型 方法名([参数类型 参数名, ...]) {
    // 方法体
}
```

**常见填空模式**：
```java
// 填空：返回类型
public ______ draw() { ... }                    // 答：void

// 填空：抽象方法（无方法体，用分号结尾）
public ______ void draw();                      // 答：abstract

// 填空：静态工厂方法
public ______ Product createProduct() { ... }   // 答：static

// 填空：子类构造方法第一行
public Circle() {
    ______("Circle");  // 答：super
}
```

## 6. 集合框架

| Java 接口 | Java 常用实现 | Python 等价 |
|-----------|-------------|-------------|
| `List<E>` | `ArrayList<E>` | `list` |
| `Set<E>` | `HashSet<E>` | `set` |
| `Map<K,V>` | `HashMap<K,V>` | `dict` |

```java
List<String> names = new ArrayList<String>();
names.add("张三");
String first = names.get(0);

Map<String, Integer> scores = new HashMap<>();
scores.put("张三", 90);
int score = scores.get("张三");
```

## 7. 异常处理

```java
// Java
try {
    riskyOperation();
} catch (IOException e) {
    handleError();
} finally {
    cleanup();  // 不论是否异常都执行
}
```

```python
# Python
try:
    risky_operation()
except IOError as e:
    handle_error()
finally:
    cleanup()
```

## 8. 泛型

```java
// Java 写接口时常见
interface Observer<T> {
    void update(T data);
}

class ConcreteObserver implements Observer<String> {
    public void update(String data) { ... }
}
```

```python
# Python 3.12+ 有泛型语法，但软考不涉及
from typing import TypeVar, Generic
T = TypeVar('T')
class Observer(Generic[T]):
    def update(self, data: T): ...
```

## 9. 设计模式常见代码骨架

### 单例模式（Singleton）
```java
public class Singleton {
    private static Singleton instance;          // 填空1：private static
    private Singleton() {}                      // 填空2：private（防止外部 new）
    public static Singleton getInstance() {     // 填空3：static
        if (instance == null) {                 // 填空4：null
            instance = new Singleton();         // 填空5：new
        }
        return instance;
    }
}
```

### 工厂方法（Factory Method）
```java
abstract class Creator {
    public abstract Product factoryMethod();    // 填空：abstract
}

class ConcreteCreator extends Creator {          // 填空：extends
    public Product factoryMethod() {
        return new ConcreteProduct();           // 填空：new
    }
}
```

### 策略模式（Strategy）
```java
interface Strategy {                            // 填空：interface
    void execute();
}

class Context {
    private Strategy strategy;                  // 组合
    public void setStrategy(Strategy s) {       // 填空：Strategy
        this.strategy = s;
    }
}
```

## 10. 易错点总结

| 易错点 | 正确写法 | 错误写法 |
|--------|---------|---------|
| 抽象方法不能有 `{}` | `abstract void draw();` | `abstract void draw() {}` |
| 接口方法默认是 `abstract` | `void draw();` (接口中) | 不写 `abstract` 也可以 |
| `implements` vs `extends` | 接口用 `implements`，类用 `extends` | 混用 |
| 构造方法无返回类型 | `public Dog() {}` | `public void Dog() {}` |
| `this()` 必须在第一行 | `this(x);` + 其他代码 | 其他代码 + `this(x);` |
