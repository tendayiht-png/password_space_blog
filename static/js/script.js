// Simple script for enhanced interactivity

document.addEventListener('DOMContentLoaded', function() {
    // Add smooth scrolling for anchor links
    const links = document.querySelectorAll('a[href^="#"]');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#' && document.querySelector(href)) {
                e.preventDefault();
                document.querySelector(href).scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Add animation delay to reveal elements
    const reveals = document.querySelectorAll('.reveal');
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    reveals.forEach(reveal => {
        reveal.style.opacity = '0';
        observer.observe(reveal);
    });

    // Add active state to navigation based on current page
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Reuse the floating arrow as Back to Top on home and Back to Home elsewhere.
    const backHomeArrow = document.getElementById('backHomeArrow');
    if (backHomeArrow) {
        const isHomePage = window.location.pathname === '/';

        if (isHomePage) {
            backHomeArrow.setAttribute('aria-label', 'Back to Top');
            backHomeArrow.setAttribute('title', 'Back to Top');
        }

        const toggleBackHomeArrow = function() {
            const shouldShow = window.scrollY > 180;
            backHomeArrow.classList.toggle('visible', shouldShow);
        };

        backHomeArrow.addEventListener('click', function(event) {
            if (!isHomePage) {
                return;
            }

            event.preventDefault();
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        toggleBackHomeArrow();
        window.addEventListener('scroll', toggleBackHomeArrow, { passive: true });
    }
});
