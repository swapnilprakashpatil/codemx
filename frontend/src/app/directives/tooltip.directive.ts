import { Directive, Input, ElementRef, OnDestroy, Renderer2, HostListener } from '@angular/core';

@Directive({
  selector: '[appTooltip]',
  standalone: true,
})
export class TooltipDirective implements OnDestroy {
  @Input('appTooltip') tooltipText = '';

  private tooltipEl: HTMLElement | null = null;
  private showTimeout: any = null;
  private hideTimeout: any = null;
  private readonly SHOW_DELAY = 300;
  private readonly HIDE_DELAY = 100;

  constructor(private el: ElementRef, private renderer: Renderer2) {}

  @HostListener('mouseenter')
  onMouseEnter(): void {
    if (!this.tooltipText) return;
    this.cancelHide();
    this.showTimeout = setTimeout(() => this.show(), this.SHOW_DELAY);
  }

  @HostListener('mouseleave')
  onMouseLeave(): void {
    this.cancelShow();
    this.hideTimeout = setTimeout(() => this.hide(), this.HIDE_DELAY);
  }

  @HostListener('click')
  onClick(): void {
    this.cancelShow();
    this.hide();
  }

  private show(): void {
    if (this.tooltipEl) return;

    this.tooltipEl = this.renderer.createElement('div');
    this.renderer.addClass(this.tooltipEl, 'cmx-tooltip');

    // Split on en-dash to bold the code portion
    const parts = this.tooltipText.split(' \u2013 ');
    if (parts.length >= 2) {
      const codePart = this.renderer.createElement('strong');
      this.renderer.appendChild(codePart, this.renderer.createText(parts[0]));
      this.renderer.appendChild(this.tooltipEl, codePart);
      this.renderer.appendChild(this.tooltipEl, this.renderer.createText(' \u2013 ' + parts.slice(1).join(' \u2013 ')));
    } else {
      this.renderer.appendChild(this.tooltipEl, this.renderer.createText(this.tooltipText));
    }

    // Append to body to avoid overflow clipping
    this.renderer.appendChild(document.body, this.tooltipEl);

    // Add host styling
    this.renderer.addClass(this.el.nativeElement, 'has-tooltip');

    this.positionTooltip();
  }

  private positionTooltip(): void {
    if (!this.tooltipEl) return;

    const hostRect = this.el.nativeElement.getBoundingClientRect();
    const scrollY = window.scrollY || document.documentElement.scrollTop;
    const scrollX = window.scrollX || document.documentElement.scrollLeft;

    // Temporarily make visible to measure
    this.renderer.setStyle(this.tooltipEl, 'visibility', 'hidden');
    this.renderer.setStyle(this.tooltipEl, 'display', 'block');

    const tipRect = this.tooltipEl.getBoundingClientRect();
    const gap = 8;

    // Default: show above
    let top = hostRect.top + scrollY - tipRect.height - gap;
    let arrowClass = 'cmx-tooltip--above';

    // If not enough room above, show below
    if (hostRect.top - tipRect.height - gap < 0) {
      top = hostRect.bottom + scrollY + gap;
      arrowClass = 'cmx-tooltip--below';
    }

    // Center horizontally
    let left = hostRect.left + scrollX + (hostRect.width / 2) - (tipRect.width / 2);

    // Clamp to viewport
    const viewportWidth = document.documentElement.clientWidth;
    if (left < 8) left = 8;
    if (left + tipRect.width > viewportWidth - 8) {
      left = viewportWidth - tipRect.width - 8;
    }

    this.renderer.setStyle(this.tooltipEl, 'top', `${top}px`);
    this.renderer.setStyle(this.tooltipEl, 'left', `${left}px`);
    this.renderer.addClass(this.tooltipEl, arrowClass);
    this.renderer.removeStyle(this.tooltipEl, 'visibility');
  }

  private hide(): void {
    if (this.tooltipEl) {
      this.renderer.removeChild(document.body, this.tooltipEl);
      this.tooltipEl = null;
    }
    this.renderer.removeClass(this.el.nativeElement, 'has-tooltip');
  }

  private cancelShow(): void {
    if (this.showTimeout) {
      clearTimeout(this.showTimeout);
      this.showTimeout = null;
    }
  }

  private cancelHide(): void {
    if (this.hideTimeout) {
      clearTimeout(this.hideTimeout);
      this.hideTimeout = null;
    }
  }

  ngOnDestroy(): void {
    this.cancelShow();
    this.cancelHide();
    this.hide();
  }
}
