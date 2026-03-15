export default function FieldError({ message }) {
  if (!message) return null;
  const displayMessage =
    message === true ? "Please fill out this field" : message;

  return (
    <div className="absolute left-0 top-full z-10 mt-1 w-max rounded-md border border-gray-800 bg-gray-950 px-3 py-1.5 text-sm text-white shadow-lg">
      {displayMessage}
    </div>
  );
}
