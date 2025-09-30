import React from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";

const Avatar = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full",
      className
    )}
    {...props}
  />
));
Avatar.displayName = "Avatar";

const AvatarImage = React.forwardRef<
  HTMLImageElement,
  React.ImgHTMLAttributes<HTMLImageElement> & { src?: string }
>(({ className, alt = "", src, ...props }, _ref) => {
  if (!src) return null;

  // Filter out incompatible props for Next.js Image
  const { width: _width, height: _height, loading: _loading, decoding: _decoding, fetchPriority: _fetchPriority, crossOrigin: _crossOrigin, ...restProps } = props;

  return (
    <Image
      src={src}
      alt={alt}
      fill
      className={cn("aspect-square object-cover", className)}
      {...restProps}
    />
  );
});
AvatarImage.displayName = "AvatarImage";

const AvatarFallback = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "flex h-full w-full items-center justify-center rounded-full bg-muted",
      className
    )}
    {...props}
  />
));
AvatarFallback.displayName = "AvatarFallback";

export { Avatar, AvatarImage, AvatarFallback };
