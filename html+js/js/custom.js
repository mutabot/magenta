/*=============================================================
    Authour URL: www.designbootstrap.com
    
    http://www.designbootstrap.com/

    License: MIT

    http://opensource.org/licenses/MIT

    100% Free To use For Personal And Commercial Use.

    IN EXCHANGE JUST TELL PEOPLE ABOUT THIS WEBSITE
   
========================================================  */

$(document).ready(function () {

/*====================================
SCROLLING SCRIPTS
======================================*/

$('.scroll-me a').bind('click', function (event) { //just pass scroll-me in design and start scrolling
var $anchor = $(this);
$('html, body').stop().animate({
scrollTop: $($anchor.attr('href')).offset().top
}, 1200, 'easeInOutExpo');
event.preventDefault();
});


/*====================================
SLIDER SCRIPTS
======================================*/


$('#carousel-slider').carousel({
interval: 2000 //TIME IN MILLI SECONDS
});


/*====================================
VAGAS SLIDESHOW SCRIPTS
======================================*/
    $.vegas('slideshow',
        {
            backgrounds:
                [
                    { src: '/img/stock/20131230.747.jpg', valign: 'top', fade: 5000, delay: 99999 },
                    //{ src: '/img/stock/20041231.041.jpg', align: 'right', fade: 1000, delay: 3000 },
                ],
            walk: function (index, slideSettings) {
                $.vegas('pause');
            }
        })
        ('overlay', { src: '/js/vegas/overlays/26.png' });


/*====================================
WRITE YOUR CUSTOM SCRIPTS BELOW
======================================*/

});
