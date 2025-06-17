// gpio_extension.c
#include <Python.h>
#include <pthread.h>
#include <time.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>

#define GPIO_BASE_ADDR 0x10000000
#define GPIO_MAP_SIZE  0x1000

#define REG_SET(offset) ((offset) + 0x630)
#define REG_CLR(offset) ((offset) + 0x640)
#define REG_DIR(offset) ((offset) + 0x600)

static volatile uint32_t *gpio_base = NULL;

static void sleep_precise(double seconds) {
    struct timespec ts;
    ts.tv_sec = (time_t)seconds;
    ts.tv_nsec = (long)((seconds - ts.tv_sec) * 1e9);
    nanosleep(&ts, NULL);
}

typedef struct {
    PyObject_HEAD
    int pin;
    bool invert;
    double frequency;
    double duty_cycle;
    pthread_t thread;
    bool running;
} GPIOObject;

static void *pwm_loop(void *arg) {
    GPIOObject *self = (GPIOObject *)arg;
    int reg_offset = (self->pin < 32) ? 0 : 4;
    int pin = (self->pin < 32) ? self->pin : self->pin - 32;

    uint32_t bit = 1 << pin;
    volatile uint32_t *set = gpio_base + (REG_SET(reg_offset) / 4);
    volatile uint32_t *clr = gpio_base + (REG_CLR(reg_offset) / 4);
    struct timespec start, end;
    long elapsed_ms;

    while (self->running) {
        double period = 1.0 / self->frequency;
        double on_time = period * self->duty_cycle;
        double off_time = period - on_time;
        
        if (self->invert) {
            *clr = bit;
            clock_gettime(CLOCK_MONOTONIC, &start);
            sleep_precise(on_time);
            clock_gettime(CLOCK_MONOTONIC, &end);
            elapsed_ms = (end.tv_sec - start.tv_sec) * 1000 + (end.tv_nsec - start.tv_nsec) / 1000000;
            printf("Pin %d: ON sleep requested %.2f ms, actual %ld ms\n", self->pin, on_time * 1000, elapsed_ms);
            
            *set = bit;
            clock_gettime(CLOCK_MONOTONIC, &start);
            sleep_precise(off_time);
            clock_gettime(CLOCK_MONOTONIC, &end);
            elapsed_ms = (end.tv_sec - start.tv_sec) * 1000 + (end.tv_nsec - start.tv_nsec) / 1000000;
            printf("Pin %d: OFF sleep requested %.2f ms, actual %ld ms\n", self->pin, off_time * 1000, elapsed_ms);
        } else {
            *set = bit;
            clock_gettime(CLOCK_MONOTONIC, &start);
            sleep_precise(on_time);
            clock_gettime(CLOCK_MONOTONIC, &end);
            elapsed_ms = (end.tv_sec - start.tv_sec) * 1000 + (end.tv_nsec - start.tv_nsec) / 1000000;
            printf("Pin %d: ON sleep requested %.2f ms, actual %ld ms\n", self->pin, on_time * 1000, elapsed_ms);
            
            *clr = bit;
            clock_gettime(CLOCK_MONOTONIC, &start);
            sleep_precise(off_time);
            clock_gettime(CLOCK_MONOTONIC, &end);
            elapsed_ms = (end.tv_sec - start.tv_sec) * 1000 + (end.tv_nsec - start.tv_nsec) / 1000000;
            printf("Pin %d: OFF sleep requested %.2f ms, actual %ld ms\n", self->pin, off_time * 1000, elapsed_ms);
        }
    }
    return NULL;
}

static PyObject *GPIO_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    GPIOObject *self = (GPIOObject *)type->tp_alloc(type, 0);
    return (PyObject *)self;
}

static int GPIO_init(GPIOObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"pin", "invert", NULL};
    int pin;
    int invert = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "i|p", kwlist, &pin, &invert))
        return -1;

    if (!gpio_base) {
        int mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
        if (mem_fd < 0) {
            PyErr_SetString(PyExc_RuntimeError, "Unable to open /dev/mem");
            return -1;
        }
        gpio_base = mmap(NULL, GPIO_MAP_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, GPIO_BASE_ADDR);
        close(mem_fd);
        if (gpio_base == MAP_FAILED) {
            PyErr_SetString(PyExc_RuntimeError, "Failed to mmap GPIO");
            return -1;
        }
    }

    self->pin = pin;
    self->invert = invert;
    self->frequency = 1000.0;
    self->duty_cycle = 0.5;
    self->running = true;

    int reg_offset = (pin < 32) ? 0 : 4;
    int real_pin = (pin < 32) ? pin : pin - 32;
    uint32_t bit = 1 << real_pin;
    volatile uint32_t *dir = gpio_base + (REG_DIR(reg_offset) / 4);
    *dir |= bit;

    pthread_create(&self->thread, NULL, pwm_loop, self);
    return 0;
}

static void GPIO_dealloc(GPIOObject *self) {
    self->running = false;
    pthread_join(self->thread, NULL);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *GPIO_set_frequency(GPIOObject *self, PyObject *args) {
    double freq;
    if (!PyArg_ParseTuple(args, "d", &freq))
        return NULL;
    self->frequency = freq;
    Py_RETURN_NONE;
}

static PyObject *GPIO_set_duty_cycle(GPIOObject *self, PyObject *args) {
    double duty;
    if (!PyArg_ParseTuple(args, "d", &duty))
        return NULL;
    if (duty < 0.0 || duty > 1.0) {
        PyErr_SetString(PyExc_ValueError, "Duty cycle must be between 0.0 and 1.0");
        return NULL;
    }
    self->duty_cycle = duty;
    Py_RETURN_NONE;
}

static PyMethodDef GPIO_methods[] = {
    {"set_frequency", (PyCFunction)GPIO_set_frequency, METH_VARARGS, "Set the PWM frequency."},
    {"set_duty_cycle", (PyCFunction)GPIO_set_duty_cycle, METH_VARARGS, "Set the PWM duty cycle."},
    {NULL}
};

static PyTypeObject GPIOType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "gpio_extension.GPIO",
    .tp_basicsize = sizeof(GPIOObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = GPIO_new,
    .tp_init = (initproc)GPIO_init,
    .tp_dealloc = (destructor)GPIO_dealloc,
    .tp_methods = GPIO_methods,
};

static PyModuleDef gpiomodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "gpio_extension",
    .m_doc = "Low-level GPIO PWM extension",
    .m_size = -1,
};

PyMODINIT_FUNC PyInit_gpio_extension(void) {
    PyObject *m;
    if (PyType_Ready(&GPIOType) < 0)
        return NULL;

    m = PyModule_Create(&gpiomodule);
    if (!m)
        return NULL;

    Py_INCREF(&GPIOType);
    PyModule_AddObject(m, "GPIO", (PyObject *)&GPIOType);
    return m;
}
